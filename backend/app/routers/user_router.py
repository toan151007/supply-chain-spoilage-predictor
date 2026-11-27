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

Writing is split by intent, not by table shape: PUT /users/{id} for the
profile, PUT /users/{id}/permissions for the seven switches (plus the
baseline role) and PUT /users/{id}/status for the active flag. Each one only
needs to know about the fields its screen actually shows.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyodbc import Error as PyodbcError
from starlette.concurrency import run_in_threadpool

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import CurrentUser, require_role
from app.schemas.common import Page
from app.schemas.user_schema import (
    UserCreate,
    UserCreated,
    UserPermissionsResult,
    UserPermissionsUpdate,
    UserRead,
    UserStatusUpdate,
    UserUpdate,
)
from app.security import hash_password
from app.services.email_service import (
    EmailDeliveryError,
    EmailNotConfiguredError,
    send_account_info_email,
)
from app.sp_helpers import as_bit

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role("owner"))],
)

HTTP_403_FORBIDDEN = status.HTTP_403_FORBIDDEN
HTTP_422_UNPROCESSABLE_CONTENT = 422

logger = logging.getLogger(__name__)

NOT_SENT_MESSAGE = "Đã tạo tài khoản nhưng chưa gửi được mail."

# Self-lockout guards. The UI also disables these fields, but the API is the
# trust boundary: a hand-built request must not be able to demote an owner.
SELF_ROLE_MESSAGE = "Không thể tự thay đổi vai trò của chính mình"
SELF_PERMISSION_MESSAGE = "Không thể tự thu hồi quyền hạn của chính mình"
SELF_DEACTIVATE_MESSAGE = "Không thể tự khoá tài khoản của mình"
SELF_DELETE_MESSAGE = "Không thể tự xóa tài khoản của mình"

PERMISSION_FIELDS = (
    "can_edit_product",
    "can_delete_product",
    "can_view_report",
    "can_manage_inventory",
    "can_manage_order",
    "can_manage_transfer",
    "can_manage_user",
)

# Starting point for a role that has no active member yet. Must match
# ROLE_DEFAULTS in frontend/src/pages/UsersPage.jsx and the CASE block inside
# sp_Users_Create (migration 018).
ROLE_DEFAULT_PERMISSIONS = {
    "owner": {field: True for field in PERMISSION_FIELDS},
    "manager": {
        **{field: True for field in PERMISSION_FIELDS},
        "can_delete_product": False,
        "can_manage_user": False,
    },
    "staff": {
        **{field: True for field in PERMISSION_FIELDS},
        "can_edit_product": False,
        "can_delete_product": False,
        "can_view_report": False,
        "can_manage_user": False,
    },
}

# Roles whose permission set is shared by every active member.
INHERITED_ROLES = ("manager", "staff")


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


def _save_row(db: DbSession, user_id: int, row: dict) -> dict:
    """
    Write a whole row back through sp_Users_Update.

    `PasswordHash` is always None here, which the procedure reads as "keep the
    current hash". Used by the permissions and status endpoints, where the
    password must never be part of the round trip.
    """
    for field in PERMISSION_FIELDS:
        row.setdefault(field, False)

    params = _write_params(row)
    params["UserId"] = user_id
    params["PasswordHash"] = None
    return db.one("sp_Users_Update", params)


def _permission_params(row: dict) -> dict:
    """Build the parameter dict of sp_Users_UpdatePermissionsByRole."""
    return {
        "Role": row["role"],
        "CanEditProduct": as_bit(row.get("can_edit_product", False)),
        "CanDeleteProduct": as_bit(row.get("can_delete_product", False)),
        "CanViewReport": as_bit(row.get("can_view_report", False)),
        "CanManageInventory": as_bit(row.get("can_manage_inventory", False)),
        "CanManageOrder": as_bit(row.get("can_manage_order", False)),
        "CanManageTransfer": as_bit(row.get("can_manage_transfer", False)),
        "CanManageUser": as_bit(row.get("can_manage_user", False)),
    }


def _role_flags(db: DbSession, role: str, exclude_user_id: int | None = None) -> dict:
    """
    Return the permission set currently used by the active members of `role`.

    Used when an account changes role through PUT /users/{id}: the new member
    must inherit what the role already has, not reset the whole role. Falls
    back to the documented defaults when the role has no active member other
    than the account being moved.
    """
    if role not in ROLE_DEFAULT_PERMISSIONS:
        return dict(ROLE_DEFAULT_PERMISSIONS["staff"])

    sets = db.call(
        "sp_Users_List",
        {
            "Search": None,
            "Role": role,
            "IsActive": 1,
            "Page": 1,
            "PageSize": 50,
        },
    )
    members = sets[1] if len(sets) > 1 else []
    for member in members:
        if member["user_id"] != exclude_user_id:
            return {field: bool(member.get(field)) for field in PERMISSION_FIELDS}

    return dict(ROLE_DEFAULT_PERMISSIONS[role])


async def _deliver_account_email(
    to_email: str,
    full_name: str,
    username: str,
    password: str,
) -> tuple[bool, str]:
    """
    Best-effort delivery of the credentials notice.

    Returns (sent, message) and never raises: the account already exists by
    the time this runs, so an SMTP problem must not turn a 201 into a 500.
    """
    try:
        await send_account_info_email(
            to_email=to_email,
            username=username,
            password=password,
            full_name=full_name,
        )
    except EmailNotConfiguredError:
        logger.warning("Account created for %s but SMTP is not configured", to_email)
        return (
            False,
            "Tạo thành công nhưng chưa gửi được mail: "
            "máy chủ chưa cấu hình SMTP (MAIL_USERNAME / MAIL_PASSWORD).",
        )
    except EmailDeliveryError as exc:
        logger.warning("Account created for %s but email failed: %s", to_email, exc)
        return False, NOT_SENT_MESSAGE

    return True, f"Đã tạo tài khoản và gửi thông tin về email {to_email}."


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
    response_model=UserCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def create_user(
    payload: UserCreate, db: DbSession = Depends(get_db)
) -> UserCreated:
    """
    Create the account, then try to email the credentials.

    Permission flags are NOT taken from the request: `sp_Users_Create` assigns
    the defaults of the chosen role (migration 018), because the role owns the
    permission set. The `Can*` keys `_write_params` still adds are ignored by
    the procedure.

    Order matters: the row is written first and the message is best-effort.
    A dead SMTP server must not lose the account the administrator just
    filled in - the UI shows "created but not sent" instead.
    """
    data = payload.model_dump()
    params = _write_params(data)
    params["PasswordHash"] = _hash_or_422(data["password"])

    try:
        created = await run_in_threadpool(db.one, "sp_Users_Create", params)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    email_sent = False
    email_message: str | None = None
    to_email = (created.get("email") or "").strip() if created else ""

    if to_email:
        email_sent, email_message = await _deliver_account_email(
            to_email=to_email,
            full_name=created.get("full_name") or data["full_name"],
            username=created.get("username") or data["username"],
            password=data["password"],
        )
    else:
        email_message = "Tài khoản không có email nên chưa gửi thông báo."

    return UserCreated(
        **created,
        email_sent=email_sent,
        email_message=email_message,
    )


@router.put("/{user_id}", response_model=UserRead, summary="Update an account")
def update_user(
    user_id: int,
    payload: UserUpdate,
    current: CurrentUser,
    db: DbSession = Depends(get_db),
) -> dict:
    """
    Update an account.

    Optional `payload` fields mean "unchanged". For the caller's own account
    the role, the permission flags and the active switch are frozen: there is
    no self-service way back in once an owner demotes or disables itself.

    Changing `role` here is allowed, but the account then joins the permission
    set the new role already uses (see `_role_flags`) instead of carrying the
    old role's flags across. The permissions tab is still the normal path for
    role changes, because that screen also lets the administrator review the
    seven switches before saving.
    """
    changes = payload.model_dump(exclude_unset=True)

    try:
        existing = _get_row_or_404(db, user_id)

        if user_id == current["user_id"]:
            if "role" in changes and changes["role"] != existing["role"]:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=SELF_ROLE_MESSAGE,
                )

            revoked = [
                field
                for field in PERMISSION_FIELDS
                if changes.get(field) is False and existing.get(field)
            ]
            if revoked:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=SELF_PERMISSION_MESSAGE,
                )

            if changes.get("is_active") is False and existing.get("is_active"):
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=SELF_DEACTIVATE_MESSAGE,
                )

        merged = {**existing, **{k: v for k, v in changes.items() if k != "password"}}
        for field in PERMISSION_FIELDS:
            merged.setdefault(field, False)

        new_role = changes.get("role")
        if new_role and new_role != existing["role"]:
            merged.update(_role_flags(db, new_role, exclude_user_id=user_id))

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


@router.put(
    "/{user_id}/permissions",
    response_model=UserPermissionsResult,
    summary="Grant or revoke permission flags (applies to the whole role)",
)
def update_user_permissions(
    user_id: int,
    payload: UserPermissionsUpdate,
    current: CurrentUser,
    db: DbSession = Depends(get_db),
) -> dict:
    """
    Save the permission switches and propagate them to the role.

    With role-based inheritance the seven flags belong to the role, not to one
    account: `sp_Users_UpdatePermissionsByRole` writes the target row and then
    every ACTIVE account with the same role (manager / staff). Owner is not
    inherited, so editing an owner only touches that owner.

    The permissions tab never shows a username or an email, so routing that
    save through PUT /users/{id} would mean resending profile fields the
    administrator did not touch. This endpoint only merges the switches (and
    the optional baseline role) into the stored row.

    The same self-lockout guards as PUT /users/{id} apply: an owner cannot
    demote itself or switch off its own permissions from here either.
    """
    # None means "unchanged", so drop it before merging.
    changes = payload.model_dump(exclude_none=True)

    try:
        existing = _get_row_or_404(db, user_id)

        if user_id == current["user_id"]:
            if "role" in changes and changes["role"] != existing["role"]:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=SELF_ROLE_MESSAGE,
                )

            revoked = [
                field
                for field in PERMISSION_FIELDS
                if changes.get(field) is False and existing.get(field)
            ]
            if revoked:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=SELF_PERMISSION_MESSAGE,
                )

        merged = {**existing, **changes}
        for field in PERMISSION_FIELDS:
            merged.setdefault(field, False)

        params = _permission_params(merged)
        params["UserId"] = user_id
        sets = db.call("sp_Users_UpdatePermissionsByRole", params)

        row = sets[0][0] if sets and sets[0] else None
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        meta = sets[1][0] if len(sets) > 1 and sets[1] else {}
        return {
            **row,
            "affected_users": int(meta.get("affected_users") or 1),
            "affected_role": meta.get("affected_role") or merged["role"],
        }
    except HTTPException:
        raise
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


@router.put(
    "/{user_id}/status",
    response_model=UserRead,
    summary="Lock or unlock an account",
)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    current: CurrentUser,
    db: DbSession = Depends(get_db),
) -> dict:
    """
    Flip only `is_active`.

    Keeping this separate keeps locking an account from becoming a
    read-modify-write of every column on the page: the row is fetched, one
    field changes, and the stored procedure keeps the last-active-owner rule.
    """
    if user_id == current["user_id"] and not payload.is_active:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=SELF_DEACTIVATE_MESSAGE,
        )

    try:
        existing = _get_row_or_404(db, user_id)
        return _save_row(db, user_id, {**existing, "is_active": payload.is_active})
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
            status_code=HTTP_403_FORBIDDEN,
            detail=SELF_DELETE_MESSAGE,
        )

    try:
        db.call("sp_Users_Delete", {"UserId": user_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None
