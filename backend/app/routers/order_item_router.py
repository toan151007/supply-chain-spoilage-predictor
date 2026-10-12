"""
CRUD router for order-items (chi tiet dong hang).

All database access goes through the SQLAlchemy ORM - no raw SQL here, as
required by the project rules.

Two invariants this router is responsible for:

1. `line_total` is a GENERATED ALWAYS AS ... STORED column. It is never
   assigned in Python - the ORM declares it with `Computed(persisted=True)`
   and the value is only ever read back with `db.refresh()`. Writing to it
   raises "cannot update a generated column".

2. `orders.total_amount` / `orders.total_quantity` are plain columns, so
   every insert, update and delete here recalculates them for the parent
   order from `SUM(line_total)` and `SUM(quantity)`. Without that the order
   header would drift away from its own lines after the first edit.

Editing a line is blocked once its order is settled (completed or
cancelled) - see `app/routers/order_router.py` for the reasoning.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, OrderItem, Product
from app.schemas.order_item_schema import (
    OrderItemCreate,
    OrderItemPage,
    OrderItemRead,
    OrderItemUpdate,
)
from app.schemas.product_schema import ProductBrief

router = APIRouter(prefix="/order-items", tags=["order-items"])

HTTP_422_UNPROCESSABLE_CONTENT = 422

# Mirrors LOCKED_STATUSES in the orders router.
LOCKED_STATUSES = {"completed", "cancelled"}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _get_item_or_404(db: Session, order_item_id: int) -> OrderItem:
    """Load one line with its parent order, or raise 404."""
    line = db.execute(
        select(OrderItem)
        .join(Order, Order.order_id == OrderItem.order_id)
        .where(OrderItem.order_item_id == order_item_id)
    ).scalar_one_or_none()

    if line is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order item {order_item_id} not found",
        )
    return line


def _editable_or_409(db: Session, order_id: int) -> Order:
    """
    Return the parent order, or 409 when it is settled.

    Applies to updates and deletes. Inserting a line into a completed order
    is blocked for the same reason - the invoiced figure must not move.
    """
    order = db.get(Order, order_id)
    if order is None:  # pragma: no cover - callers check this first
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    if order.status in LOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Order {order_id} is {order.status} and can no longer be "
                "edited. Only pending orders are editable."
            ),
        )
    return order


def _recalculate_order_totals(db: Session, order_id: int) -> None:
    """
    Rewrite the parent order's counters from its lines.

    The session is created with `autoflush=False` (see app/database.py), so
    a pending INSERT or UPDATE is invisible to the SUM below unless it is
    flushed first. Without this flush the totals would be recomputed from
    the previous state and the order header would disagree with its lines.

    Commits as part of the caller's transaction, so a failure anywhere in
    the request rolls back the line edit and this recalculation together.
    No commit here: the caller decides when the unit of work ends.
    """
    db.flush()

    total_amount, total_quantity = db.execute(
        select(
            func.coalesce(func.sum(OrderItem.line_total), 0),
            func.coalesce(func.sum(OrderItem.quantity), 0),
        ).where(OrderItem.order_id == order_id)
    ).one()

    order = db.get(Order, order_id)
    if order is None:  # pragma: no cover
        return

    order.total_amount = total_amount
    order.total_quantity = total_quantity


def _to_read(db: Session, line: OrderItem) -> OrderItemRead:
    """Build the response body, including the product stub."""
    data = OrderItemRead.model_validate(line)
    product = db.get(Product, line.product_id)
    data.product = ProductBrief.model_validate(product) if product else None
    return data


def _attach_products(db: Session, lines: list[OrderItem]) -> list[OrderItemRead]:
    """Load product stubs for a whole page of lines in ONE query."""
    if not lines:
        return []

    products = db.execute(
        select(Product).where(
            Product.product_id.in_({line.product_id for line in lines})
        )
    ).scalars().all()
    stubs = {p.product_id: ProductBrief.model_validate(p) for p in products}

    result = []
    for line in lines:
        data = OrderItemRead.model_validate(line)
        data.product = stubs.get(line.product_id)
        result.append(data)
    return result


# --------------------------------------------------------------------------
# Read endpoints
# --------------------------------------------------------------------------
@router.get("", response_model=OrderItemPage, summary="List order lines")
def list_order_items(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number, starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Rows per page, max 100"),
    order_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    store_id: int | None = Query(
        None, gt=0, description="Filter by the parent order's store"
    ),
    min_line_total: float | None = Query(None, ge=0),
    max_line_total: float | None = Query(None, ge=0),
) -> OrderItemPage:
    """
    Paginated line list, newest order first.

    `min_line_total` / `max_line_total` filter on the generated column,
    which PostgreSQL evaluates with the same expression used when it was
    stored.
    """
    if (
        min_line_total is not None
        and max_line_total is not None
        and min_line_total > max_line_total
    ):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_line_total must be less than or equal to max_line_total",
        )

    filters = []
    if order_id is not None:
        filters.append(OrderItem.order_id == order_id)
    if product_id is not None:
        filters.append(OrderItem.product_id == product_id)
    if store_id is not None:
        filters.append(Order.order_id == OrderItem.order_id)
        filters.append(Order.store_id == store_id)
    if min_line_total is not None:
        filters.append(OrderItem.line_total >= min_line_total)
    if max_line_total is not None:
        filters.append(OrderItem.line_total <= max_line_total)

    total = db.execute(
        select(func.count())
        .select_from(OrderItem)
        .where(*filters)
    ).scalar_one()

    lines = list(
        db.execute(
            select(OrderItem)
            .where(*filters)
            .order_by(OrderItem.order_id.desc(), OrderItem.order_item_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
    )

    pages = (total + page_size - 1) // page_size
    return OrderItemPage(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=_attach_products(db, lines),
    )


@router.get("/{order_item_id}", response_model=OrderItemRead, summary="Get one line")
def get_order_item(order_item_id: int, db: Session = Depends(get_db)) -> OrderItemRead:
    line = _get_item_or_404(db, order_item_id)
    return _to_read(db, line)


# --------------------------------------------------------------------------
# Write endpoints
# --------------------------------------------------------------------------
@router.post(
    "", response_model=OrderItemRead, status_code=status.HTTP_201_CREATED,
    summary="Add a line to an order",
)
def create_order_item(
    payload: OrderItemCreate, db: Session = Depends(get_db)
) -> OrderItemRead:
    """
    Append a line and refresh the parent order's totals.

    The table carries UNIQUE (order_id, product_id), so adding a product
    the order already contains returns 409. Sending the same product twice
    is almost always a double click; merging into the existing line is a
    PUT on that line, which is explicit about intent.
    """
    if db.get(Order, payload.order_id) is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Order {payload.order_id} does not exist",
        )
    if db.get(Product, payload.product_id) is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Product {payload.product_id} does not exist",
        )

    _editable_or_409(db, payload.order_id)

    line = OrderItem(
        order_id=payload.order_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        unit_cost=payload.unit_cost,
        discount_percent=payload.discount_percent,
        # line_total intentionally omitted - GENERATED column.
    )
    db.add(line)

    try:
        # The recalculation flushes first, so the UNIQUE violation on
        # (order_id, product_id) surfaces HERE rather than at commit.
        # Everything that can raise IntegrityError has to sit inside this
        # block, otherwise the client gets a 500 instead of a 409.
        _recalculate_order_totals(db, payload.order_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Order {payload.order_id} already contains product "
                f"{payload.product_id}. Update the existing line instead."
            ),
        ) from exc

    # Refresh to read the generated line_total back from the database.
    db.refresh(line)
    return _to_read(db, line)


@router.put(
    "/{order_item_id}", response_model=OrderItemRead, summary="Update a line"
)
def update_order_item(
    order_item_id: int, payload: OrderItemUpdate, db: Session = Depends(get_db)
) -> OrderItemRead:
    """
    Partially update a line and refresh the parent order's totals.

    Changing `product_id` can collide with a product the order already
    holds, which the UNIQUE constraint turns into a 409.
    """
    line = _get_item_or_404(db, order_item_id)
    _editable_or_409(db, line.order_id)

    changes = payload.model_dump(exclude_unset=True)

    new_product_id = changes.get("product_id")
    if new_product_id is not None and new_product_id != line.product_id:
        if db.get(Product, new_product_id) is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Product {new_product_id} does not exist",
            )

    if not changes:
        db.refresh(line)
        return _to_read(db, line)

    for field, value in changes.items():
        setattr(line, field, value)

    try:
        # Same as create: the flush inside the recalculation is what
        # raises the UNIQUE violation, so it must be inside the handler.
        _recalculate_order_totals(db, line.order_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Order {line.order_id} already contains product "
                f"{new_product_id}"
            ),
        ) from exc

    db.refresh(line)
    return _to_read(db, line)


@router.delete(
    "/{order_item_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a line",
)
def delete_order_item(order_item_id: int, db: Session = Depends(get_db)) -> None:
    """
    Delete a line and refresh the parent order's totals.

    Removing the last line leaves the order at 0/0 and still deletable.
    That is a legitimate way to cancel an order entered by mistake without
    losing the record that it existed.
    """
    line = _get_item_or_404(db, order_item_id)
    order_id = line.order_id

    _editable_or_409(db, order_id)

    db.delete(line)

    try:
        # flushes internally, so the SUM no longer counts the deleted row
        _recalculate_order_totals(db, order_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete this line",
        ) from exc
