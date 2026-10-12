"""
CRUD router for products.

All database access goes through the SQLAlchemy ORM - no raw SQL here,
as required by the project rules.

DELETE is expected to fail for products that already have history: the
`products` table is referenced with ON DELETE RESTRICT by `order_items`,
`inventory`, `inventory_transactions` and `forecasts`. That is correct
behaviour - sales history must not be silently deleted - so a failed
delete returns HTTP 409 with a clear message instead of a 500.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.dependencies import require_role
from app.database import get_db
from app.models import Category, Product
from app.schemas.product_schema import (
    ProductCreate,
    ProductPage,
    ProductRead,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["products"])

# Starlette deprecated `HTTP_422_UNPROCESSABLE_ENTITY` in favour of
# `HTTP_422_UNPROCESSABLE_CONTENT`. Both mean 422; using the new name keeps
# the deprecation warning out of the logs.
HTTP_422_UNPROCESSABLE_CONTENT = 422


def _get_product_or_404(db: Session, product_id: int) -> Product:
    """Load one product with its category, or raise 404."""
    product = db.execute(
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.product_id == product_id)
    ).scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    return product


@router.get("", response_model=ProductPage, summary="List products with pagination")
def list_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number, starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Rows per page, max 100"),
    category_id: int | None = Query(None, gt=0, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active flag"),
    search: str | None = Query(
        None, min_length=1, max_length=255,
        description="Case-insensitive match on product code or name",
    ),
) -> ProductPage:
    """
    Return a paginated product list.

    Default page size is 20 and the maximum is 100. The cap matters because
    the products table is read together with its category for every row.
    """
    filters = []
    if category_id is not None:
        filters.append(Product.category_id == category_id)
    if is_active is not None:
        filters.append(Product.is_active.is_(is_active))
    if search:
        pattern = f"%{search}%"
        filters.append(
            Product.product_name.ilike(pattern) | Product.product_code.ilike(pattern)
        )

    total = db.execute(
        select(func.count()).select_from(Product).where(*filters)
    ).scalar_one()

    query = (
        select(Product)
        .options(joinedload(Product.category))
        .where(*filters)
        .order_by(Product.product_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.execute(query).scalars().all()

    # Ceiling division so an empty result set reports 0 pages, not 1.
    pages = (total + page_size - 1) // page_size

    return ProductPage(
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{product_id}", response_model=ProductRead, summary="Get one product")
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    return _get_product_or_404(db, product_id)


@router.post(
    "", response_model=ProductRead, status_code=status.HTTP_201_CREATED,
    summary="Create a product",
 dependencies=[Depends(require_role('owner', 'manager'))],)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    """Insert a new product.

    `product_code` and `product_name` are not exposed as unique in the
    schema, but the database has UNIQUE constraints on both, so a
    duplicate raises IntegrityError and is turned into HTTP 409.
    """
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Category {payload.category_id} does not exist",
        )

    product = Product(**payload.model_dump())
    db.add(product)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product code or name already exists",
        ) from exc

    db.refresh(product)
    return product


@router.put(
    "/{product_id}", response_model=ProductRead, summary="Update a product"
, dependencies=[Depends(require_role('owner', 'manager'))])
def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)
) -> Product:
    """
    Partially update a product.

    Fields absent from the request body keep their current value, so this
    behaves like a merge rather than a full replace.
    """
    product = _get_product_or_404(db, product_id)

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        # Nothing to change - return the current state untouched.
        return product

    new_category_id = changes.get("category_id")
    if new_category_id is not None and new_category_id != product.category_id:
        if db.get(Category, new_category_id) is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Category {new_category_id} does not exist",
            )

    for field, value in changes.items():
        setattr(product, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product code or name already exists, or max_stock < min_stock",
        ) from exc

    db.refresh(product)
    return product


@router.delete(
    "/{product_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
 dependencies=[Depends(require_role('owner', 'manager'))],)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> None:
    """
    Delete a product that has no history.

    Returns 409 when the product is referenced by sales, stock or forecast
    rows. This is the normal outcome for this dataset: every one of the 50
    seeded products already has order_items rows, because product_id 1-50
    map directly to the Kaggle item ids. Use `is_active = false` to retire
    a product instead of deleting it.
    """
    product = _get_product_or_404(db, product_id)

    db.delete(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot delete: the product is referenced by orders, stock or "
                "forecasts. Set is_active to false instead."
            ),
        ) from exc