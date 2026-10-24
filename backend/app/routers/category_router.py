"""
CRUD router for categories (B3 - SQL Server Stored Procedure).

Categories form a two-level hierarchy (`parent_category_id` references the
same table). The procedures already block the two mistakes that would
corrupt the tree:

  - making a category its own parent (50004 -> 409)
  - re-parenting under one of its own descendants (50004 -> 409)

`sp_Categories_Delete` also detaches children before deleting the row, since
SQL Server cannot cascade on a self-referencing foreign key.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import require_role
from app.schemas.category_schema import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/categories", tags=["categories"])


def _get_row_or_404(db: DbSession, category_id: int) -> dict:
    row = db.one("sp_Categories_Get", {"CategoryId": category_id})
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )
    return row


@router.get("", response_model=Page[CategoryRead], summary="List categories")
def list_categories(
    db: DbSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    parent_id: int | None = None,
    roots_only: bool = False,
) -> Page[CategoryRead]:
    try:
        sets = db.call(
            "sp_Categories_List",
            {
                "Search": search,
                "ParentCategoryId": parent_id,
                "RootsOnly": 1 if roots_only else 0,
                "Page": page,
                "PageSize": page_size,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    total = int(sets[0][0]["total"]) if sets and sets[0] else 0
    items = sets[1] if len(sets) > 1 else []
    pages = (total + page_size - 1) // page_size
    return Page[CategoryRead](
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{category_id}", response_model=CategoryRead, summary="Get one category")
def get_category(category_id: int, db: DbSession = Depends(get_db)) -> dict:
    try:
        return _get_row_or_404(db, category_id)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.post(
    "", response_model=CategoryRead, status_code=status.HTTP_201_CREATED,
    summary="Create a category",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def create_category(payload: CategoryCreate, db: DbSession = Depends(get_db)) -> dict:
    data = payload.model_dump()
    try:
        return db.one(
            "sp_Categories_Create",
            {
                "CategoryName": data["category_name"],
                "Description": data["description"],
                "ParentCategoryId": data["parent_category_id"],
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.put(
    "/{category_id}", response_model=CategoryRead, summary="Update a category",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def update_category(
    category_id: int, payload: CategoryUpdate, db: DbSession = Depends(get_db)
) -> dict:
    try:
        current = _get_row_or_404(db, category_id)
        merged = {**current, **payload.model_dump(exclude_unset=True)}
        return db.one(
            "sp_Categories_Update",
            {
                "CategoryId": category_id,
                "CategoryName": merged["category_name"],
                "Description": merged["description"],
                "ParentCategoryId": merged["parent_category_id"],
            },
        )
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.delete(
    "/{category_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def delete_category(category_id: int, db: DbSession = Depends(get_db)) -> None:
    try:
        db.call("sp_Categories_Delete", {"CategoryId": category_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None
