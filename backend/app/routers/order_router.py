"""
CRUD router for orders (don hang).

All database access goes through the SQLAlchemy ORM - no raw SQL here, as
required by the project rules.

Two things in this router deserve an explanation.

1. `total_amount` and `total_quantity` are ordinary columns, not generated
   ones. Nothing in PostgreSQL keeps them in step with `order_items`, so
   `_recalculate_order_totals` recomputes them from `SUM(line_total)` and
   `SUM(quantity)` on every write that can change a line. The list endpoint
   derives the per-row counters for a whole page in a single GROUP BY, so
   page size does not change the number of queries.

2. Line edits are blocked on settled orders. `completed` and `cancelled`
   orders represent transactions that have already been invoiced or
   reversed; silently editing them would make the sales history disagree
   with the stock movements derived from it. Only `pending` orders are
   editable, and only certain status transitions are allowed - see
   `ALLOWED_TRANSITIONS`.

Prices are MOCK values assigned per product group - the Kaggle dataset has
no price column. Never present these figures as real revenue.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.models import Order, OrderItem, Product, Store, User
from app.schemas.order_item_schema import OrderItemRead
from app.schemas.order_schema import (
    OrderCreate,
    OrderDetail,
    OrderPage,
    OrderRead,
    OrderStatusUpdate,
    OrderUpdate,
)
from app.schemas.product_schema import ProductBrief

router = APIRouter(prefix="/orders", tags=["orders"])

HTTP_422_UNPROCESSABLE_CONTENT = 422

# Orders in these states are settled and must not be edited.
LOCKED_STATUSES = {"completed", "cancelled"}

# Allowed status transitions. Anything not listed is rejected with 409.
# - pending -> completed / cancelled : the normal path.
# - cancelled -> pending            : reopen a wrongly cancelled order.
# - completed -> *                  : never. The order has been invoiced and
#   stock has already moved, so reversing it needs a compensating entry,
#   not a status flip.
# A transition to the current status is always allowed and is a no-op, which
# matches the idempotent contract of PUT /api/v1/alerts/{id}/read.
ALLOWED_TRANSITIONS = {
    "pending": {"pending", "completed", "cancelled"},
    "cancelled": {"cancelled", "pending"},
    "completed": {"completed"},
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _get_order_or_404(db: Session, order_id: int) -> Order:
    """Load one order with its store, or raise 404."""
    order = db.execute(
        select(Order)
        .options(joinedload(Order.store))
        .where(Order.order_id == order_id)
    ).scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return order


def _line_count(db: Session, order_id: int) -> int:
    return db.execute(
        select(func.count())
        .select_from(OrderItem)
        .where(OrderItem.order_id == order_id)
    ).scalar_one()


def _attach_products(db: Session, lines: list[OrderItem]) -> list[OrderItemRead]:
    """
    Load product stubs for a set of lines in ONE query.

    Touching `line.product` inside a loop would emit one SELECT per line -
    50 queries for a typical order here. Collecting the distinct
    `product_id`s first keeps it at one.
    """
    product_ids = {line.product_id for line in lines}
    if not product_ids:
        return []

    products = db.execute(
        select(Product).where(Product.product_id.in_(product_ids))
    ).scalars().all()
    stubs = {p.product_id: ProductBrief.model_validate(p) for p in products}

    return [
        OrderItemRead.model_validate(
            {**OrderItemRead.model_validate(line).model_dump(),
             "product": stubs.get(line.product_id)}
        )
        for line in lines
    ]


def _recalculate_order_totals(db: Session, order: Order) -> None:
    """
    Refresh the denormalised counters on `orders` from its lines.

    Reads `SUM(line_total)` - the generated column - so the stored figure
    is PostgreSQL's own arithmetic rather than a re-implementation of the
    formula. Commits only when a value actually moved, so a no-op write
    does not churn the `trg_orders_updated` trigger.

    Both SUMs are NULL for an order with no lines; `coalesce` turns that
    into 0 because the columns are NOT NULL.

    The explicit flush is required: the session runs with `autoflush=False`
    (see app/database.py), so a pending write would otherwise be invisible
    to the SUM.
    """
    db.flush()

    total_amount, total_quantity = db.execute(
        select(
            func.coalesce(func.sum(OrderItem.line_total), 0),
            func.coalesce(func.sum(OrderItem.quantity), 0),
        ).where(OrderItem.order_id == order.order_id)
    ).one()

    if (
        order.total_amount == total_amount
        and order.total_quantity == total_quantity
    ):
        return

    order.total_amount = total_amount
    order.total_quantity = total_quantity
    db.commit()


def _attach_derived_counts(
    db: Session, orders: list[Order]
) -> dict[int, tuple[int, float]]:
    """
    Count lines and total quantity for a whole page in ONE query.

    A per-order lookup would be the classic N+1 pattern. Grouping by
    `order_id` keeps it at a single query no matter how large the page is.
    """
    if not orders:
        return {}

    rows = db.execute(
        select(
            OrderItem.order_id,
            func.count(OrderItem.order_item_id),
            func.coalesce(func.sum(OrderItem.quantity), 0),
        )
        .where(OrderItem.order_id.in_([o.order_id for o in orders]))
        .group_by(OrderItem.order_id)
    ).all()

    return {order_id: (count, qty) for order_id, count, qty in rows}


def _to_read(order: Order, counts: dict[int, tuple[int, float]]) -> OrderRead:
    """Build the response body, filling the two derived counters."""
    data = OrderRead.model_validate(order)
    line_count, total_items = counts.get(order.order_id, (0, 0))
    data.line_count = line_count
    # SUM(quantity) over a NUMERIC column comes back as Decimal. Casting
    # here keeps Pydantic from warning about a Decimal landing in a float
    # field, and matches how the model columns themselves are converted.
    data.total_items = float(total_items)
    return data


def _to_detail(
    db: Session, order: Order, counts: dict[int, tuple[int, float]]
) -> OrderDetail:
    """Build the response body including every line."""
    base = _to_read(order, counts).model_dump()
    return OrderDetail(**base, items=_attach_products(db, list(order.items)))


# --------------------------------------------------------------------------
# Read endpoints
# --------------------------------------------------------------------------
@router.get("", response_model=OrderPage, summary="List orders with pagination")
def list_orders(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number, starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Rows per page, max 100"),
    store_id: int | None = Query(None, gt=0),
    order_type: str | None = Query(None, pattern="^(sale|purchase)$"),
    status_filter: str | None = Query(
        None, alias="status", pattern="^(pending|completed|cancelled)$",
        description="Filter by order state",
    ),
    from_date: datetime | None = Query(
        None, description="Inclusive lower bound on order_date"
    ),
    to_date: datetime | None = Query(
        None, description="Inclusive upper bound on order_date"
    ),
    order_id: int | None = Query(None, gt=0, description="Filter by exact order_id"),
) -> OrderPage:
    """
    Return a paginated order list, newest first.

    Ordered by `order_date DESC` with `order_id DESC` as the tie-break.
    Without the tie-break, orders sharing a timestamp can come back in a
    different order between two requests, which makes pagination skip or
    repeat rows - the dataset holds 3,650 orders per year in date batches.
    """
    if (
        from_date is not None
        and to_date is not None
        and from_date > to_date
    ):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="from_date must be earlier than or equal to to_date",
        )

    filters = []
    if store_id is not None:
        filters.append(Order.store_id == store_id)
    if order_type is not None:
        filters.append(Order.order_type == order_type)
    if status_filter is not None:
        filters.append(Order.status == status_filter)
    if from_date is not None:
        filters.append(Order.order_date >= from_date)
    if to_date is not None:
        filters.append(Order.order_date <= to_date)
    if order_id is not None:
        filters.append(Order.order_id == order_id)

    total = db.execute(
        select(func.count()).select_from(Order).where(*filters)
    ).scalar_one()

    orders = list(
        db.execute(
            select(Order)
            .options(joinedload(Order.store))
            .where(*filters)
            .order_by(Order.order_date.desc(), Order.order_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
    )

    counts = _attach_derived_counts(db, orders)
    pages = (total + page_size - 1) // page_size

    return OrderPage(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=[_to_read(o, counts) for o in orders],
    )


@router.get(
    "/{order_id}", response_model=OrderDetail, summary="Get one order with its lines"
)
def get_order(order_id: int, db: Session = Depends(get_db)) -> OrderDetail:
    """
    Return one order together with all of its lines.

    Lines are loaded with `selectinload`, which issues one extra query for
    the whole set of children rather than one per parent.
    """
    order = db.execute(
        select(Order)
        .options(joinedload(Order.store), selectinload(Order.items))
        .where(Order.order_id == order_id)
    ).unique().scalar_one_or_none()

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )

    return _to_detail(db, order, _attach_derived_counts(db, [order]))


@router.get(
    "/{order_id}/items",
    response_model=list[OrderItemRead],
    summary="List the lines of one order",
)
def list_order_items(
    order_id: int, db: Session = Depends(get_db)
) -> list[OrderItemRead]:
    """Return only the lines of one order, in insertion order."""
    _get_order_or_404(db, order_id)

    lines = db.execute(
        select(OrderItem)
        .where(OrderItem.order_id == order_id)
        .order_by(OrderItem.order_item_id)
    ).scalars().all()

    return _attach_products(db, list(lines))


# --------------------------------------------------------------------------
# Write endpoints
# --------------------------------------------------------------------------
@router.post(
    "", response_model=OrderDetail, status_code=status.HTTP_201_CREATED,
    summary="Create an order together with its lines",
)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> OrderDetail:
    """
    Insert an order and its lines in one transaction.

    The header starts at 0/0, the lines are added, then the totals are
    recomputed from `SUM(line_total)`. If any line is rejected the whole
    transaction rolls back - an order holding half its lines would leave the
    counters disagreeing with the lines that do exist.

    New orders default to `pending` rather than to the column default
    `completed`. An order becomes completed only once someone confirms it.
    """
    if db.get(Store, payload.store_id) is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Store {payload.store_id} does not exist",
        )
    if payload.user_id is not None and db.get(User, payload.user_id) is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"User {payload.user_id} does not exist",
        )

    product_ids = [line.product_id for line in payload.items]
    known = set(
        db.execute(
            select(Product.product_id).where(Product.product_id.in_(product_ids))
        ).scalars().all()
    )
    missing = sorted(set(product_ids) - known)
    if missing:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown product_id: {missing}",
        )

    order = Order(
        order_code=payload.order_code,
        store_id=payload.store_id,
        order_type=payload.order_type,
        # The column is timestamptz, so the default must be aware or
        # PostgreSQL rejects the insert with "timestamp with time zone
        # cannot be used with naive datetime".
        order_date=payload.order_date or datetime.now(timezone.utc),
        status=payload.status,
        payment_method=payload.payment_method,
        customer_name=payload.customer_name,
        user_id=payload.user_id,
        note=payload.note,
        total_amount=0,
        total_quantity=0,
    )
    db.add(order)

    try:
        # Inside the try on purpose: the flush is what actually issues the
        # INSERT, so a duplicate `order_code` raises IntegrityError HERE.
        # Left outside, the exception would escape the handler and the
        # client would get a 500 instead of a 409.
        db.flush()  # assign order_id without committing yet
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="order_code already exists",
        ) from exc

    for line in payload.items:
        db.add(
            OrderItem(
                order_id=order.order_id,
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                unit_cost=line.unit_cost,
                discount_percent=line.discount_percent,
                # line_total intentionally omitted - the database generates it.
            )
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="order_code already exists, or a product is duplicated in items",
        ) from exc

    _recalculate_order_totals(db, order)
    db.refresh(order)

    # Re-read through get_order so the response is built by exactly the same
    # code path as a normal fetch.
    return get_order(order.order_id, db)


@router.put("/{order_id}", response_model=OrderRead, summary="Update an order")
def update_order(
    order_id: int, payload: OrderUpdate, db: Session = Depends(get_db)
) -> OrderRead:
    """
    Partially update an order header.

    Refuses to touch `completed` or `cancelled` orders - see the module
    docstring. Status has its own endpoint so the transition rules live in
    one place.
    """
    order = _get_order_or_404(db, order_id)

    if order.status in LOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Order {order_id} is {order.status} and can no longer be "
                "edited. Only pending orders are editable."
            ),
        )

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return _to_read(order, _attach_derived_counts(db, [order]))

    new_store_id = changes.get("store_id")
    if new_store_id is not None and new_store_id != order.store_id:
        if db.get(Store, new_store_id) is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Store {new_store_id} does not exist",
            )

    new_user_id = changes.get("user_id")
    if new_user_id is not None and db.get(User, new_user_id) is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"User {new_user_id} does not exist",
        )

    for field, value in changes.items():
        setattr(order, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="order_code already exists"
        ) from exc

    db.refresh(order)
    return _to_read(order, _attach_derived_counts(db, [order]))


@router.put(
    "/{order_id}/status", response_model=OrderRead,
    summary="Change the status of an order",
)
def update_order_status(
    order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)
) -> OrderRead:
    """
    Move an order through its lifecycle.

    Setting the status an order already has is accepted and does nothing.
    A transition outside `ALLOWED_TRANSITIONS` returns 409.
    """
    order = _get_order_or_404(db, order_id)

    allowed = ALLOWED_TRANSITIONS[order.status]
    if payload.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot move an order from {order.status} to {payload.status}. "
                f"Allowed from {order.status}: {sorted(allowed)}"
            ),
        )

    order.status = payload.status
    db.commit()
    db.refresh(order)
    return _to_read(order, _attach_derived_counts(db, [order]))


@router.delete(
    "/{order_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an order"
)
def delete_order(order_id: int, db: Session = Depends(get_db)) -> None:
    """
    Delete an order that has no lines, returning 409 otherwise.

    The foreign key on `order_items.order_id` is ON DELETE CASCADE, so
    PostgreSQL would happily take the lines down with the order. This
    endpoint blocks that on purpose: dropping 50 lines by accident is not
    recoverable through the API, and a caller who really wants them gone
    can delete them explicitly first.
    """
    order = _get_order_or_404(db, order_id)

    count = _line_count(db, order_id)
    if count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete order {order_id}: it still has {count} "
                "line(s). Delete them first."
            ),
        )

    db.delete(order)
    db.commit()
