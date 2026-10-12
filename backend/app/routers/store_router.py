"""
CRUD router for stores.

A store cannot be deleted once it has sales history: `orders.store_id`
uses ON DELETE RESTRICT, so removing a store would orphan order records.
Other tables cascade (inventory, forecasts, alerts, users). Rather than
losing data silently, a failed delete returns HTTP 409 and suggests
deactivating the store instead.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Store
from app.schemas.common import Message, Page
from app.schemas.store_schema import StoreCreate, StoreRead, StoreUpdate

router = APIRouter(prefix="/stores", tags=["stores"])

HTTP_422_UNPROCESSABLE_CONTENT = 422


def _get_store_or_404(db: Session, store_id: int) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store {store_id} not found",
        )
    return store


@router.get("", response_model=Page[StoreRead], summary="List stores")
def list_stores(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_type: str | None = Query(
        None, pattern="^(convenience_store|restaurant|warehouse)$"
    ),
    is_active: bool | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=255),
) -> Page[StoreRead]:
    """Paginated store list with optional type, active and search filters."""
    filters = []
    if store_type is not None:
        filters.append(Store.store_type == store_type)
    if is_active is not None:
        filters.append(Store.is_active.is_(is_active))
    if search:
        pattern = f"%{search}%"
        filters.append(Store.store_name.ilike(pattern) | Store.store_code.ilike(pattern))

    total = db.execute(
        select(func.count()).select_from(Store).where(*filters)
    ).scalar_one()

    items = db.execute(
        select(Store).where(*filters).order_by(Store.store_id)
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    pages = (total + page_size - 1) // page_size
    return Page[StoreRead](
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{store_id}", response_model=StoreRead, summary="Get one store")
def get_store(store_id: int, db: Session = Depends(get_db)) -> Store:
    return _get_store_or_404(db, store_id)


@router.post(
    "", response_model=StoreRead, status_code=status.HTTP_201_CREATED,
    summary="Create a store",
)
def create_store(payload: StoreCreate, db: Session = Depends(get_db)) -> Store:
    store = Store(**payload.model_dump())
    db.add(store)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Store code {payload.store_code} already exists",
        ) from exc

    db.refresh(store)
    return store


@router.put("/{store_id}", response_model=StoreRead, summary="Update a store")
def update_store(
    store_id: int, payload: StoreUpdate, db: Session = Depends(get_db)
) -> Store:
    store = _get_store_or_404(db, store_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(store, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Store code {changes.get('store_code', store.store_code)} already exists",
        ) from exc

    db.refresh(store)
    return store


@router.delete(
    "/{store_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a store",
)
def delete_store(store_id: int, db: Session = Depends(get_db)) -> None:
    """
    Delete a store that has no sales history.

    All 10 seeded stores have thousands of orders, so in practice this
    returns 409. Use `is_active = false` to close a store.
    """
    store = _get_store_or_404(db, store_id)
    db.delete(store)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot delete: the store has orders and is referenced by "
                "existing records. Set is_active to false instead."
            ),
        ) from exc