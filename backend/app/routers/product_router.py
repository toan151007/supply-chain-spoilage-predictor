"""
CRUD router for products (B3 - SQL Server Stored Procedure).

All database access goes through `EXEC dbo.sp_Products_*`; there is no ORM
query in this file. The update contract is "send the COMPLETE row", so a
partial PUT is merged into the current row before the call - that keeps
"field omitted" (keep current) different from "field set to null" (clear).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import require_role
from app.schemas.product_schema import (
    ProductCreate,
    ProductPage,
    ProductRead,
    ProductUpdate,
)
from app.sp_helpers import as_bit, attach_category

router = APIRouter(prefix="/products", tags=["products"])


def _to_read(row: dict) -> dict:
    return attach_category(dict(row))


def _get_row_or_404(db: DbSession, product_id: int) -> dict:
    row = db.one("sp_Products_Get", {"ProductId": product_id})
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    return row


@router.get("", response_model=ProductPage, summary="List products with pagination")
def list_products(
    db: DbSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number, starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Rows per page, max 100"),
    category_id: int | None = Query(None, gt=0, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active flag"),
    search: str | None = Query(
        None, min_length=1, max_length=255,
        description="Case-insensitive match on product code or name",
    ),
) -> ProductPage:
    try:
        sets = db.call(
            "sp_Products_List",
            {
                "Search": search,
                "CategoryId": category_id,
                "IsActive": as_bit(is_active),
                "Page": page,
                "PageSize": page_size,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    total = int(sets[0][0]["total"]) if sets and sets[0] else 0
    items = [_to_read(row) for row in (sets[1] if len(sets) > 1 else [])]
    pages = (total + page_size - 1) // page_size
    return ProductPage(
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{product_id}", response_model=ProductRead, summary="Get one product")
def get_product(product_id: int, db: DbSession = Depends(get_db)) -> dict:
    try:
        return _to_read(_get_row_or_404(db, product_id))
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.post(
    "", response_model=ProductRead, status_code=status.HTTP_201_CREATED,
    summary="Create a product",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def create_product(payload: ProductCreate, db: DbSession = Depends(get_db)) -> dict:
    data = payload.model_dump()
    try:
        row = db.one(
            "sp_Products_Create",
            {
                "ProductCode": data["product_code"],
                "ProductName": data["product_name"],
                "CategoryId": data["category_id"],
                "Unit": data["unit"],
                "UnitCost": data["unit_cost"],
                "SellingPrice": data["selling_price"],
                "ShelfLifeDays": data["shelf_life_days"],
                "MinStock": data["min_stock"],
                "MaxStock": data["max_stock"],
                "IsPerishable": as_bit(data["is_perishable"]),
                "ReorderPoint": data["reorder_point"],
                "Supplier": data["supplier"],
                "IsActive": as_bit(data["is_active"]),
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Create succeeded but the row could not be read back",
        )
    return _to_read(row)


@router.put(
    "/{product_id}", response_model=ProductRead, summary="Update a product",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def update_product(
    product_id: int, payload: ProductUpdate, db: DbSession = Depends(get_db)
) -> dict:
    try:
        current = _get_row_or_404(db, product_id)
        changes = payload.model_dump(exclude_unset=True)
        merged = {**current, **changes}

        row = db.one(
            "sp_Products_Update",
            {
                "ProductId": product_id,
                "ProductCode": merged["product_code"],
                "ProductName": merged["product_name"],
                "CategoryId": merged["category_id"],
                "Unit": merged["unit"],
                "UnitCost": merged["unit_cost"],
                "SellingPrice": merged["selling_price"],
                "ShelfLifeDays": merged["shelf_life_days"],
                "MinStock": merged["min_stock"],
                "MaxStock": merged["max_stock"],
                "IsPerishable": as_bit(merged["is_perishable"]),
                "ReorderPoint": merged["reorder_point"],
                "Supplier": merged["supplier"],
                "IsActive": as_bit(merged["is_active"]),
            },
        )
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return _to_read(row)


@router.delete(
    "/{product_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def delete_product(product_id: int, db: DbSession = Depends(get_db)) -> None:
    try:
        db.call("sp_Products_Delete", {"ProductId": product_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None
