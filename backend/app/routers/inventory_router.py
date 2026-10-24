"""
CRUD router for inventory / stock batches (B3 - SQL Server Stored Procedure).

A product at a store can sit in several batches with different expiry dates,
so a batch is identified by UNIQUE (store_id, product_id, expiry_date). The
procedure raises 50002 when that triple already exists and the router maps it
to 409.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import require_role
from app.schemas.common import Page
from app.schemas.inventory_schema import (
    ExpiringReport,
    InventoryCreate,
    InventoryRead,
    InventoryUpdate,
)
from app.sp_helpers import attach_product, attach_store

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _to_read(row: dict) -> dict:
    row = dict(row)
    attach_store(row)
    attach_product(row)
    return row


def _get_row_or_404(db: DbSession, inventory_id: int) -> dict:
    row = db.one("sp_Inventory_Get", {"InventoryId": inventory_id})
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory batch {inventory_id} not found",
        )
    return row


# NOTE: `/expiring` must be declared BEFORE `/{inventory_id}`. FastAPI
# matches routes in order; the int path parameter would try to parse
# "expiring" and answer 422 instead of reaching this handler.
@router.get(
    "/expiring", response_model=ExpiringReport,
    summary="Batches expiring within N days",
)
def list_expiring(
    db: DbSession = Depends(get_db),
    days: int = Query(7, ge=1, le=365, description="Window in days"),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    include_expired: bool = Query(
        True, description="Include batches already past their expiry date"
    ),
) -> ExpiringReport:
    try:
        # The view behind the procedure covers a fixed 30-day window, so a
        # larger `days` cannot widen the result.
        sets = db.call(
            "sp_Inventory_ListExpiring",
            {
                "Days": min(days, 30),
                "StoreId": store_id,
                "ProductId": product_id,
                "IncludeExpired": 1 if include_expired else 0,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    items = []
    for row in (sets[0] if sets else []):
        row = dict(row)
        attach_product(row)
        items.append(row)

    return ExpiringReport(
        days=days, as_of=date.today(), total=len(items), items=items
    )


@router.get("", response_model=Page[InventoryRead], summary="List stock batches")
def list_inventory(
    db: DbSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    expiry_date: date | None = Query(None, description="Exact expiry date"),
    expiry_before: date | None = Query(None, description="Expiry date on or before"),
    in_stock_only: bool = Query(False, description="Only batches with quantity > 0"),
) -> Page[InventoryRead]:
    try:
        sets = db.call(
            "sp_Inventory_List",
            {
                "StoreId": store_id,
                "ProductId": product_id,
                "ExpiryDate": expiry_date,
                "ExpiryBefore": expiry_before,
                "InStockOnly": 1 if in_stock_only else 0,
                "Page": page,
                "PageSize": page_size,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    total = int(sets[0][0]["total"]) if sets and sets[0] else 0
    items = [_to_read(row) for row in (sets[1] if len(sets) > 1 else [])]
    pages = (total + page_size - 1) // page_size
    return Page[InventoryRead](
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{inventory_id}", response_model=InventoryRead, summary="Get one batch")
def get_inventory(inventory_id: int, db: DbSession = Depends(get_db)) -> dict:
    try:
        return _to_read(_get_row_or_404(db, inventory_id))
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.post(
    "", response_model=InventoryRead, status_code=status.HTTP_201_CREATED,
    summary="Create a stock batch",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def create_inventory(
    payload: InventoryCreate, db: DbSession = Depends(get_db)
) -> dict:
    data = payload.model_dump()
    try:
        row = db.one(
            "sp_Inventory_Create",
            {
                "StoreId": data["store_id"],
                "ProductId": data["product_id"],
                "ExpiryDate": data["expiry_date"],
                "Quantity": data["quantity"],
                "ReceivedDate": data["received_date"],
                "BatchCode": data["batch_code"],
            },
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Batch was created but could not be read back",
            )
        return _to_read(row)
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.put(
    "/{inventory_id}", response_model=InventoryRead, summary="Update a stock batch",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def update_inventory(
    inventory_id: int, payload: InventoryUpdate, db: DbSession = Depends(get_db)
) -> dict:
    try:
        current = _get_row_or_404(db, inventory_id)
        merged = {**current, **payload.model_dump(exclude_unset=True)}
        db.call(
            "sp_Inventory_Update",
            {
                "InventoryId": inventory_id,
                "ExpiryDate": merged["expiry_date"],
                "Quantity": merged["quantity"],
                "ReceivedDate": merged["received_date"],
                "BatchCode": merged["batch_code"],
            },
        )
        return _to_read(_get_row_or_404(db, inventory_id))
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.delete(
    "/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a stock batch",
    dependencies=[Depends(require_role("owner", "manager", "staff"))],
)
def delete_inventory(inventory_id: int, db: DbSession = Depends(get_db)) -> None:
    try:
        db.call("sp_Inventory_Delete", {"InventoryId": inventory_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None
