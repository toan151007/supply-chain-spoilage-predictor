"""
CRUD router for order-items (B3 - SQL Server Stored Procedure).

`line_total` is a computed column in SQL Server; the procedures own it and
never accept it. Every insert, update and delete also recalculates the
parent order's `total_amount` / `total_quantity` inside the same procedure
transaction, so the header cannot drift away from its lines.

Editing a line is blocked once its order is settled (completed or cancelled).
The procedure raises 50004 and the router maps it to 409.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import require_role
from app.schemas.order_item_schema import (
    OrderItemCreate,
    OrderItemPage,
    OrderItemRead,
    OrderItemUpdate,
)
from app.sp_helpers import attach_product

router = APIRouter(prefix="/order-items", tags=["order-items"])


def _to_read(row: dict) -> dict:
    row = dict(row)
    attach_product(row)
    return row


@router.get("", response_model=OrderItemPage, summary="List order lines")
def list_order_items(
    db: DbSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    store_id: int | None = Query(None, gt=0),
    min_line_total: float | None = Query(None, ge=0),
    max_line_total: float | None = Query(None, ge=0),
) -> OrderItemPage:
    if (
        min_line_total is not None
        and max_line_total is not None
        and min_line_total > max_line_total
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_line_total must be less than or equal to max_line_total",
        )

    try:
        sets = db.call(
            "sp_OrderItems_List",
            {
                "OrderId": order_id,
                "ProductId": product_id,
                "StoreId": store_id,
                "MinLineTotal": min_line_total,
                "MaxLineTotal": max_line_total,
                "Page": page,
                "PageSize": page_size,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    total = int(sets[0][0]["total"]) if sets and sets[0] else 0
    items = [_to_read(row) for row in (sets[1] if len(sets) > 1 else [])]
    pages = (total + page_size - 1) // page_size
    return OrderItemPage(
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{order_item_id}", response_model=OrderItemRead, summary="Get one line")
def get_order_item(order_item_id: int, db: DbSession = Depends(get_db)) -> dict:
    try:
        row = db.one("sp_OrderItems_Get", {"OrderItemId": order_item_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order item {order_item_id} not found",
        )
    return _to_read(row)


@router.post(
    "", response_model=OrderItemRead, status_code=status.HTTP_201_CREATED,
    summary="Add a line to an order",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def create_order_item(
    payload: OrderItemCreate, db: DbSession = Depends(get_db)
) -> dict:
    data = payload.model_dump()
    try:
        row = db.one(
            "sp_OrderItems_Create",
            {
                "OrderId": data["order_id"],
                "ProductId": data["product_id"],
                "Quantity": data["quantity"],
                "UnitPrice": data["unit_price"],
                "UnitCost": data["unit_cost"],
                "DiscountPercent": data["discount_percent"],
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return _to_read(row)


@router.put(
    "/{order_item_id}", response_model=OrderItemRead, summary="Update a line",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def update_order_item(
    order_item_id: int, payload: OrderItemUpdate, db: DbSession = Depends(get_db)
) -> dict:
    try:
        current = db.one("sp_OrderItems_Get", {"OrderItemId": order_item_id})
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order item {order_item_id} not found",
            )
        merged = {**current, **payload.model_dump(exclude_unset=True)}
        row = db.one(
            "sp_OrderItems_Update",
            {
                "OrderItemId": order_item_id,
                "ProductId": merged["product_id"],
                "Quantity": merged["quantity"],
                "UnitPrice": merged["unit_price"],
                "UnitCost": merged["unit_cost"],
                "DiscountPercent": merged["discount_percent"],
            },
        )
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return _to_read(row)


@router.delete(
    "/{order_item_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a line",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def delete_order_item(order_item_id: int, db: DbSession = Depends(get_db)) -> None:
    try:
        db.call("sp_OrderItems_Delete", {"OrderItemId": order_item_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None

