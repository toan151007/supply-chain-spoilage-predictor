"""
CRUD router for inventory (stock batches).

A product at a store can sit in several batches with different expiry
dates, so a batch is identified by UNIQUE (store_id, product_id,
expiry_date). Expiry date lives here rather than on `products` because it
belongs to a batch, not to the product itself.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.dependencies import require_role
from app.database import get_db
from app.models import Inventory, Product, Store
from app.schemas.inventory_schema import (
    ExpiringBatch,
    ExpiringReport,
    InventoryCreate,
    InventoryRead,
    InventoryUpdate,
)
from app.schemas.common import Page

router = APIRouter(prefix="/inventory", tags=["inventory"])

HTTP_422_UNPROCESSABLE_CONTENT = 422


def _get_batch_or_404(db: Session, inventory_id: int) -> Inventory:
    batch = db.execute(
        select(Inventory)
        .options(joinedload(Inventory.store), joinedload(Inventory.product))
        .where(Inventory.inventory_id == inventory_id)
    ).scalar_one_or_none()

    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory batch {inventory_id} not found",
        )
    return batch


@router.get(
    "/expiring", response_model=ExpiringReport,
    summary="Batches expiring within N days",
)
def list_expiring(
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=365, description="Window in days"),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    include_expired: bool = Query(
        True, description="Include batches already past their expiry date"
    ),
) -> ExpiringReport:
    """
    Report batches whose expiry date falls inside the window.

    Expired rows have a negative `days_left`. They are included by default
    because an expired batch is the most urgent thing on this report; pass
    `include_expired=false` to look only at batches that are still usable.

    Only batches with `quantity > 0` are returned - an empty batch cannot
    spoil and would only add noise.
    """
    today = date.today()
    cutoff = today + timedelta(days=days)

    conditions = [
        Inventory.quantity > 0,
        Inventory.expiry_date.isnot(None),
        Inventory.expiry_date <= cutoff,
    ]
    if not include_expired:
        conditions.append(Inventory.expiry_date >= today)
    if store_id is not None:
        conditions.append(Inventory.store_id == store_id)
    if product_id is not None:
        conditions.append(Inventory.product_id == product_id)

    rows = db.execute(
        select(Inventory)
        .options(joinedload(Inventory.product))
        .where(*conditions)
        .order_by(Inventory.expiry_date)
    ).scalars().all()

    items = [
        ExpiringBatch(
            inventory_id=b.inventory_id,
            store_id=b.store_id,
            product_id=b.product_id,
            expiry_date=b.expiry_date,
            days_left=(b.expiry_date - today).days if b.expiry_date else None,
            quantity=float(b.quantity),
            product=b.product,
        )
        for b in rows
    ]

    return ExpiringReport(
        days=days, as_of=today, total=len(items), items=items
    )


@router.get("", response_model=Page[InventoryRead], summary="List stock batches")
def list_inventory(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    expiry_date: date | None = Query(None, description="Exact expiry date"),
    expiry_before: date | None = Query(None, description="Expiry date on or before"),
    in_stock_only: bool = Query(False, description="Only batches with quantity > 0"),
) -> Page[InventoryRead]:
    """Paginated stock batch list with store, product and date filters."""
    filters = []
    if store_id is not None:
        filters.append(Inventory.store_id == store_id)
    if product_id is not None:
        filters.append(Inventory.product_id == product_id)
    if expiry_date is not None:
        filters.append(Inventory.expiry_date == expiry_date)
    if expiry_before is not None:
        filters.append(Inventory.expiry_date <= expiry_before)
    if in_stock_only:
        filters.append(Inventory.quantity > 0)

    total = db.execute(
        select(func.count()).select_from(Inventory).where(*filters)
    ).scalar_one()

    items = db.execute(
        select(Inventory)
        .options(joinedload(Inventory.store), joinedload(Inventory.product))
        .where(*filters)
        .order_by(Inventory.inventory_id)
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    pages = (total + page_size - 1) // page_size
    return Page[InventoryRead](
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{inventory_id}", response_model=InventoryRead, summary="Get one batch")
def get_inventory(inventory_id: int, db: Session = Depends(get_db)) -> Inventory:
    return _get_batch_or_404(db, inventory_id)


@router.post(
    "", response_model=InventoryRead, status_code=status.HTTP_201_CREATED,
    summary="Create a stock batch",
 dependencies=[Depends(require_role('owner', 'manager', 'staff'))],)
def create_inventory(
    payload: InventoryCreate, db: Session = Depends(get_db)
) -> Inventory:
    if db.get(Store, payload.store_id) is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Store {payload.store_id} does not exist",
        )
    if db.get(Product, payload.product_id) is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Product {payload.product_id} does not exist",
        )

    batch = Inventory(**payload.model_dump())
    db.add(batch)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A batch for this store, product and expiry date already "
                "exists (UNIQUE constraint)."
            ),
        ) from exc

    db.refresh(batch)
    return _get_batch_or_404(db, batch.inventory_id)


@router.put(
    "/{inventory_id}", response_model=InventoryRead, summary="Update a stock batch"
, dependencies=[Depends(require_role('owner', 'manager', 'staff'))])
def update_inventory(
    inventory_id: int, payload: InventoryUpdate, db: Session = Depends(get_db)
) -> Inventory:
    batch = _get_batch_or_404(db, inventory_id)

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(batch, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another batch already uses this store, product and expiry date.",
        ) from exc

    db.refresh(batch)
    return batch


@router.delete(
    "/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a stock batch",
 dependencies=[Depends(require_role('owner', 'manager', 'staff'))],)
def delete_inventory(inventory_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a batch. No table has a foreign key to inventory, so this succeeds."""
    batch = _get_batch_or_404(db, inventory_id)
    db.delete(batch)
    db.commit()