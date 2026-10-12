"""
CRUD router for categories.

Categories form a two-level hierarchy (`parent_category_id` references the
same table). This router blocks two mistakes that the database would accept
but that would corrupt the tree:

  - making a category its own parent, which creates a self-loop
  - re-parenting a category under one of its own descendants, which would
    detach that whole branch from the root
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category, Product
from app.schemas.category_schema import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/categories", tags=["categories"])

HTTP_422_UNPROCESSABLE_CONTENT = 422


def _get_category_or_404(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )
    return category


def _collect_descendants(db: Session, category_id: int) -> set[int]:
    """
    Return the category plus every category below it.

    Walks the tree one level at a time. The seeded data is only two levels
    deep, but this works for any depth and avoids a recursive CTE.
    """
    seen: set[int] = set()
    frontier = [category_id]
    while frontier:
        children = db.execute(
            select(Category.category_id).where(
                Category.parent_category_id.in_(frontier)
            )
        ).scalars().all()
        # Stop if nothing new turns up, otherwise the cycle check below
        # would never trigger.
        if not children or set(children) <= seen:
            break
        seen.update(children)
        frontier = list(children)
    return seen


@router.get("", response_model=Page[CategoryRead], summary="List categories")
def list_categories(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    parent_category_id: int | None = Query(
        None, gt=0,
        description="Filter by parent. Use a dedicated root filter to get top-level.",
    ),
    roots_only: bool = Query(False, description="Return only top-level categories"),
    search: str | None = Query(None, min_length=1, max_length=150),
) -> Page[CategoryRead]:
    """Paginated category list. `roots_only` returns categories with no parent."""
    filters = []
    if roots_only:
        filters.append(Category.parent_category_id.is_(None))
    elif parent_category_id is not None:
        filters.append(Category.parent_category_id == parent_category_id)
    if search:
        filters.append(Category.category_name.ilike(f"%{search}%"))

    total = db.execute(
        select(func.count()).select_from(Category).where(*filters)
    ).scalar_one()

    items = db.execute(
        select(Category).where(*filters).order_by(Category.category_id)
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    pages = (total + page_size - 1) // page_size
    return Page[CategoryRead](
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{category_id}", response_model=CategoryRead, summary="Get one category")
def get_category(category_id: int, db: Session = Depends(get_db)) -> Category:
    return _get_category_or_404(db, category_id)


@router.post(
    "", response_model=CategoryRead, status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
def create_category(
    payload: CategoryCreate, db: Session = Depends(get_db)
) -> Category:
    if payload.parent_category_id is not None:
        _get_category_or_404(db, payload.parent_category_id)

    category = Category(**payload.model_dump())
    db.add(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category name {payload.category_name} already exists",
        ) from exc

    db.refresh(category)
    return category


@router.put(
    "/{category_id}", response_model=CategoryRead, summary="Update a category"
)
def update_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)
) -> Category:
    category = _get_category_or_404(db, category_id)
    changes = payload.model_dump(exclude_unset=True)

    new_parent = changes.get("parent_category_id")
    if new_parent is not None:
        if new_parent == category_id:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A category cannot be its own parent",
            )
        _get_category_or_404(db, new_parent)
        # Re-parenting under a descendant would orphan that branch.
        descendants = _collect_descendants(db, category_id)
        if new_parent in descendants:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Cannot move a category under one of its own "
                    "descendants - that would detach the whole branch"
                ),
            )

    for field, value in changes.items():
        setattr(category, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category name {changes.get('category_name', category.category_name)} already exists",
        ) from exc

    db.refresh(category)
    return category


@router.delete(
    "/{category_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    """
    Delete a category.

    `products.category_id` uses ON DELETE RESTRICT, so a category that
    still has products returns 409. A category that has only children is
    blocked locally: the foreign key would silently set their parent to
    NULL and they would jump up a level, which is rarely what the user
    meant.
    """
    category = _get_category_or_404(db, category_id)

    child_count = db.execute(
        select(func.count()).select_from(Category)
        .where(Category.parent_category_id == category_id)
    ).scalar_one()
    if child_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete: {child_count} sub-categories still reference "
                "this one. Move or delete them first."
            ),
        )

    product_count = db.execute(
        select(func.count()).select_from(Product)
        .where(Product.category_id == category_id)
    ).scalar_one()
    if product_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete: {product_count} products still reference "
                "this category. Move them first."
            ),
        )

    db.delete(category)
    db.commit()