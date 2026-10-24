"""
CRUD router for orders (B3 - SQL Server Stored Procedure).

All database access goes through `EXEC dbo.sp_Orders_*`. Two contracts are
owned by the procedures, not by this file:

1. `total_amount` and `total_quantity` are ordinary columns. Every procedure
   that touches a line recalculates them from `SUM(line_total)` and
   `SUM(quantity)` inside the same transaction, so the header cannot drift
   away from its lines.

2. Line edits are blocked on settled orders. `sp_Orders_Update` and
   `sp_OrderItems_*` raise 50004 for `completed` / `cancelled` orders; the
   router maps it to 409. `completed` never goes back to `pending` - that
   needs a compensating entry, not a status flip.

Prices are MOCK values: the Kaggle dataset has no price column.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import require_role
from app.schemas.order_item_schema import OrderItemRead
from app.schemas.order_schema import (
    OrderCreate,
    OrderDetail,
    OrderPage,
    OrderRead,
    OrderStatusUpdate,
    OrderUpdate,
)
from app.sp_helpers import attach_product, attach_store

router = APIRouter(prefix="/orders", tags=["orders"])

# Orders in these states are settled and must not be edited.
LOCKED_STATUSES = {"completed", "cancelled"}

# Allowed status transitions. Anything not listed is rejected with 409.
# - pending -> completed / cancelled : the normal path.
# - cancelled -> pending            : reopen a wrongly cancelled order.
# - completed -> *                  : never. The order has been invoiced and
#   stock has already moved, so reversing it needs a compensating entry,
#   not a status flip.
# A transition to the current status is always allowed and is a no-op.
ALLOWED_TRANSITIONS = {
    "pending": {"pending", "completed", "cancelled"},
    "cancelled": {"cancelled", "pending"},
    "completed": {"completed"},
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _to_read(row: dict) -> dict:
    row = dict(row)
    attach_store(row)
    return row


def _fetch_lines(db: DbSession, order_id: int) -> list[dict]:
    """
    Return every line of one order, paging because `sp_OrderItems_List`
    caps `@PageSize` at 100 while an order may hold up to 500 lines.
    """
    lines: list[dict] = []
    page = 1
    while True:
        sets = db.call(
            "sp_OrderItems_List",
            {
                "OrderId": order_id,
                "ProductId": None,
                "StoreId": None,
                "MinLineTotal": None,
                "MaxLineTotal": None,
                "Page": page,
                "PageSize": 100,
            },
        )
        batch = sets[1] if len(sets) > 1 else []
        for row in batch:
            row = dict(row)
            attach_product(row)
            lines.append(row)
        total = int(sets[0][0]["total"]) if sets and sets[0] else 0
        if page * 100 >= total or not batch:
            break
        page += 1
    return lines


def _get_row_or_404(db: DbSession, order_id: int) -> dict:
    row = db.one("sp_Orders_Get", {"OrderId": order_id})
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return row


def _to_detail(db: DbSession, row: dict) -> dict:
    data = _to_read(row)
    data["items"] = _fetch_lines(db, int(row["order_id"]))
    return data


# --------------------------------------------------------------------------
# Read endpoints
# --------------------------------------------------------------------------
@router.get("", response_model=OrderPage, summary="List orders with pagination")
def list_orders(
    db: DbSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number, starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Rows per page, max 100"),
    store_id: int | None = Query(None, gt=0),
    order_type: str | None = Query(None, pattern="^(sale|purchase)$"),
    status_filter: str | None = Query(
        None, alias="status", pattern="^(pending|completed|cancelled)$",
        description="Filter by order state",
    ),
    from_date=None,
    to_date=None,
    order_id: int | None = Query(None, gt=0, description="Filter by exact order_id"),
) -> OrderPage:
    """
    Return a paginated order list, newest first.

    Ordered by `order_date DESC` with `order_id DESC` as the tie-break so
    pagination cannot skip or repeat rows when many orders share a timestamp.
    """
    try:
        sets = db.call(
            "sp_Orders_List",
            {
                "StoreId": store_id,
                "OrderType": order_type,
                "Status": status_filter,
                "FromDate": from_date,
                "ToDate": to_date,
                "OrderId": order_id,
                "Page": page,
                "PageSize": page_size,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    total = int(sets[0][0]["total"]) if sets and sets[0] else 0
    items = [_to_read(row) for row in (sets[1] if len(sets) > 1 else [])]
    pages = (total + page_size - 1) // page_size
    return OrderPage(
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get(
    "/{order_id}", response_model=OrderDetail, summary="Get one order with its lines"
)
def get_order(order_id: int, db: DbSession = Depends(get_db)) -> dict:
    try:
        row = _get_row_or_404(db, order_id)
        return _to_detail(db, row)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.get(
    "/{order_id}/items",
    response_model=list[OrderItemRead],
    summary="List the lines of one order",
)
def list_order_items(order_id: int, db: DbSession = Depends(get_db)) -> list[dict]:
    try:
        _get_row_or_404(db, order_id)
        return _fetch_lines(db, order_id)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


# --------------------------------------------------------------------------
# Write endpoints
# --------------------------------------------------------------------------
@router.post(
    "", response_model=OrderDetail, status_code=status.HTTP_201_CREATED,
    summary="Create an order together with its lines",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def create_order(payload: OrderCreate, db: DbSession = Depends(get_db)) -> dict:
    """
    Insert an order and its lines in one transaction.

    `sp_Orders_Create` validates store, user and every product, inserts the
    lines, then recomputes the header totals. If any line is rejected the
    whole transaction rolls back - an order holding half its lines would
    leave the counters disagreeing with the lines that do exist.
    """
    items_json = json.dumps(
        [
            {
                "product_id": line.product_id,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "unit_cost": line.unit_cost,
                "discount_percent": line.discount_percent,
            }
            for line in payload.items
        ]
    )
    try:
        row = db.one(
            "sp_Orders_Create",
            {
                "OrderCode": payload.order_code,
                "StoreId": payload.store_id,
                "OrderType": payload.order_type,
                "OrderDate": payload.order_date,
                "Status": payload.status,
                "PaymentMethod": payload.payment_method,
                "CustomerName": payload.customer_name,
                "UserId": payload.user_id,
                "Note": payload.note,
                "ItemsJson": items_json,
            },
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Order was created but could not be read back",
            )
        return _to_detail(db, row)
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.put(
    "/{order_id}", response_model=OrderRead, summary="Update an order",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def update_order(
    order_id: int, payload: OrderUpdate, db: DbSession = Depends(get_db)
) -> dict:
    """
    Partially update an order header.

    Refuses to touch `completed` or `cancelled` orders. Status has its own
    endpoint so the transition rules live in one place.
    """
    try:
        current = _get_row_or_404(db, order_id)
        if current["status"] in LOCKED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Order {order_id} is {current['status']} and can no "
                    "longer be edited. Only pending orders are editable."
                ),
            )

        merged = {**current, **payload.model_dump(exclude_unset=True)}
        row = db.one(
            "sp_Orders_Update",
            {
                "OrderId": order_id,
                "OrderCode": merged["order_code"],
                "StoreId": merged["store_id"],
                "OrderType": merged["order_type"],
                "OrderDate": merged["order_date"],
                "PaymentMethod": merged["payment_method"],
                "CustomerName": merged["customer_name"],
                "UserId": merged["user_id"],
                "Note": merged["note"],
            },
        )
        return _to_read(row)
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.put(
    "/{order_id}/status", response_model=OrderRead,
    summary="Change the status of an order",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def update_order_status(
    order_id: int, payload: OrderStatusUpdate, db: DbSession = Depends(get_db)
) -> dict:
    """
    Move an order through its lifecycle.

    Setting the status an order already has is accepted and does nothing.
    A transition outside `ALLOWED_TRANSITIONS` returns 409 before the
    procedure is called, so the client gets a message naming the states.
    """
    try:
        current = _get_row_or_404(db, order_id)
        allowed = ALLOWED_TRANSITIONS[current["status"]]
        if payload.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot move an order from {current['status']} to "
                    f"{payload.status}. Allowed from {current['status']}: "
                    f"{sorted(allowed)}"
                ),
            )
        row = db.one(
            "sp_Orders_UpdateStatus",
            {"OrderId": order_id, "Status": payload.status},
        )
        return _to_read(row)
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.delete(
    "/{order_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an order",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def delete_order(order_id: int, db: DbSession = Depends(get_db)) -> None:
    """
    Delete an order and all of its lines in one transaction.

    `sp_Orders_Delete` removes the line items first, then the header, so a
    caller never has to know the child rows exist. Both statements run inside
    the procedure's transaction: either the whole order disappears or none of
    it does.
    """
    try:
        db.call("sp_Orders_Delete", {"OrderId": order_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None
