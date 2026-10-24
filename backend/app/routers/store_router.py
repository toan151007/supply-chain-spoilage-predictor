"""
CRUD router for stores (B3 - SQL Server Stored Procedure).

A store cannot be deleted once it has sales history: `orders.store_id` uses
ON DELETE RESTRICT, so removing a store would orphan order records. The
procedure raises 50003 and the router maps it to 409, suggesting
`is_active = false` instead.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import require_role
from app.schemas.common import Page
from app.schemas.store_schema import StoreCreate, StoreRead, StoreUpdate
from app.sp_helpers import as_bit

router = APIRouter(prefix="/stores", tags=["stores"])


def _get_row_or_404(db: DbSession, store_id: int) -> dict:
    row = db.one("sp_Stores_Get", {"StoreId": store_id})
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store {store_id} not found",
        )
    return row


@router.get("", response_model=Page[StoreRead], summary="List stores")
def list_stores(
    db: DbSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_type: str | None = Query(
        None, pattern="^(convenience_store|restaurant|warehouse)$"
    ),
    is_active: bool | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=255),
) -> Page[StoreRead]:
    try:
        sets = db.call(
            "sp_Stores_List",
            {
                "Search": search,
                "StoreType": store_type,
                "IsActive": as_bit(is_active),
                "Page": page,
                "PageSize": page_size,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    total = int(sets[0][0]["total"]) if sets and sets[0] else 0
    items = sets[1] if len(sets) > 1 else []
    pages = (total + page_size - 1) // page_size
    return Page[StoreRead](
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{store_id}", response_model=StoreRead, summary="Get one store")
def get_store(store_id: int, db: DbSession = Depends(get_db)) -> dict:
    try:
        return _get_row_or_404(db, store_id)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.post(
    "", response_model=StoreRead, status_code=status.HTTP_201_CREATED,
    summary="Create a store",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def create_store(payload: StoreCreate, db: DbSession = Depends(get_db)) -> dict:
    data = payload.model_dump()
    try:
        row = db.one(
            "sp_Stores_Create",
            {
                "StoreCode": data["store_code"],
                "StoreName": data["store_name"],
                "Address": data["address"],
                "Phone": data["phone"],
                "StoreType": data["store_type"],
                "OpeningDate": data["opening_date"],
                "IsActive": as_bit(data["is_active"]),
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return row


@router.put(
    "/{store_id}", response_model=StoreRead, summary="Update a store",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def update_store(
    store_id: int, payload: StoreUpdate, db: DbSession = Depends(get_db)
) -> dict:
    try:
        current = _get_row_or_404(db, store_id)
        merged = {**current, **payload.model_dump(exclude_unset=True)}
        row = db.one(
            "sp_Stores_Update",
            {
                "StoreId": store_id,
                "StoreCode": merged["store_code"],
                "StoreName": merged["store_name"],
                "Address": merged["address"],
                "Phone": merged["phone"],
                "StoreType": merged["store_type"],
                "OpeningDate": merged["opening_date"],
                "IsActive": as_bit(merged["is_active"]),
            },
        )
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return row


@router.delete(
    "/{store_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a store",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def delete_store(store_id: int, db: DbSession = Depends(get_db)) -> None:
    try:
        db.call("sp_Stores_Delete", {"StoreId": store_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None
