"""
User management CRUD (owner only).

Every database call goes through `EXEC dbo.sp_Users_*`; there is no ORM query
in this file.

Why owner-only: a manager can already change operational data, but creating
accounts and handing out permissions is the one action that can escalate
privilege. `dependencies=[Depends(require_role("owner"))]` on the router
covers every endpoint at once, so a new endpoint cannot accidentally ship
without the check.

Password handling: plain text comes in, a bcrypt hash goes to the stored
procedure. Updates leave the hash untouched when `password` is omitted, so
editing a name does not silently reset a password.

Partial update: the stored procedure expects a whole row, so the router
merges the payload into the current row before calling it. That is what lets
an omitted field mean "unchanged" instead of "set to NULL".
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import CurrentUser, require_role
from app.schemas.common import Page
from app.schemas.user_schema import UserCreate, UserRead, UserUpdate
from app.security import hash_password
from app.sp_helpers import as_bit

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role("owner"))],
)

HTTP_409_CONFLICT = status.HTTP_409_CONFLICT
HTTP_422_UNPROCESSABLE_CONTENT = 422

PERMISSION_FIELDS = (
    "can_edit_product",
    "can_delete_product",
    "can_view_report",
    "can_manage_inventory",
    "can_manage_order",
    "can_manage_transfer",
    "can_manage_user",
)


def _get_row_or_404(db: DbSession, user_id: int) -> dict:
    row = db.one("sp_Users_GetById", {"UserId": user_id})
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return row


def _hash_or_422(password: str) -> str:
    try:
        return hash_password(password)
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


def _write_params(data: dict) -> dict:
    """Translate a schema dict into the stored-procedure parameter names."""
    return {
        "Username": data["username"],
        "Email": data.get("email"),
        "FullName": data["full_name"],
        "Role": data["role"],
        "StoreId": data.get("store_id"),
        "IsActive": as_bit(data.get("is_active", True)),
        "AvatarUrl": data.get("avatar_url"),
        "CanEditProduct": as_bit(data.get("can_edit_product", False)),
        "CanDeleteProduct": as_bit(data.get("can_delete_product", False)),
        "CanViewReport": as_bit(data.get("can_view_report", False)),
        "CanManageInventory": as_bit(data.get("can_manage_inventory", False)),
        "CanManageOrder": as_bit(data.get("can_manage_order", False)),
        "CanManageTransfer": as_bit(data.get("can_manage_transfer", False)),
        "CanManageUser": as_bit(data.get("can_manage_user", False)),
    }


@router.get("", response_model=Page[UserRead], summary="List accounts")
def list_users(
    db: DbSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    role: str | None = Query(None, pattern="^(owner|manager|staff)$"),
    is_active: bool | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=150),
) -> Page[UserRead]:
    try:
        sets = db.call(
            "sp_Users_List",
            {
                "Search": search,
                "Role": role,
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
    return Page[UserRead](
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{user_id}", response_model=UserRead, summary="Get one account")
def get_user(user_id: int, db: DbSession = Depends(get_db)) -> dict:
    try:
        return _get_row_or_404(db, user_id)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def create_user(payload: UserCreate, db: DbSession = Depends(get_db)) -> dict:
    data = payload.model_dump()
    params = _write_params(data)
    params["PasswordHash"] = _hash_or_422(data["password"])

    try:
        return db.one("sp_Users_Create", params)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.put("/{user_id}", response_model=UserRead, summary="Update an account")
def update_user(
    user_id: int,
    payload: UserUpdate,
    current: CurrentUser,
    db: DbSession = Depends(get_db),
) -> dict:
    changes = payload.model_dump(exclude_unset=True)

    # An owner locking themselves out is almost always a mistake, and there
    # is no self-service way back in.
    if user_id == current["user_id"] and changes.get("is_active") is False:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="You cannot deactivate your own account",
        )

    try:
        existing = _get_row_or_404(db, user_id)

        merged = {**existing, **{k: v for k, v in changes.items() if k != "password"}}
        for field in PERMISSION_FIELDS:
            merged.setdefault(field, False)

        params = _write_params(merged)
        params["UserId"] = user_id
        params["PasswordHash"] = (
            _hash_or_422(changes["password"]) if "password" in changes else None
        )

        return db.one("sp_Users_Update", params)
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an account",
)
def delete_user(
    user_id: int,
    current: CurrentUser,
    db: DbSession = Depends(get_db),
) -> None:
    if user_id == current["user_id"]:
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="You cannot delete your own account",
        )

    try:
        db.call("sp_Users_Delete", {"UserId": user_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None
