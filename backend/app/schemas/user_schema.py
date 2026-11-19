"""
Pydantic schemas for the user management API.

The read model is the same `UserRead` used by `/auth/me`, so the frontend
only has one user shape to deal with. The permission flags mirror the
`users` columns one-for-one.

Passwords are accepted in plain text here (the API is the trust boundary)
and hashed with `app.security.hash_password` before the stored procedure is
called. `max_length=72` is bcrypt's hard limit: longer input is silently
truncated by some libraries and rejected by others, so reject it explicitly.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth_schema import UserRead


class UserCreated(UserRead):
    """
    Response for POST /api/v1/users.

    The account is always created; `email_sent` only reports whether the
    credentials notice reached the address on the form. The UI uses it to
    pick between "created and sent" and "created but not sent", so a broken
    SMTP setup never looks like a failed account.
    """

    email_sent: bool = False
    email_message: str | None = None

# Mirrors the CHECK constraint on users.role.
UserRole = str
ROLE_PATTERN = "^(owner|manager|staff)$"


class UserPermissionFields(BaseModel):
    """The toggles shown in the create/edit dialog."""

    can_edit_product: bool = False
    can_delete_product: bool = False
    can_view_report: bool = False
    can_manage_inventory: bool = False
    can_manage_order: bool = False
    can_manage_transfer: bool = False
    can_manage_user: bool = False


class UserCreate(UserPermissionFields):
    """Request body for POST /api/v1/users."""

    model_config = ConfigDict(from_attributes=True)

    username: Annotated[str, Field(min_length=1, max_length=50)]
    email: Annotated[str | None, Field(max_length=150)] = None
    password: Annotated[str, Field(min_length=6, max_length=72)]
    full_name: Annotated[str, Field(min_length=1, max_length=150)]
    role: str = Field(default="staff", pattern=ROLE_PATTERN)
    store_id: int | None = None
    is_active: bool = True
    avatar_url: Annotated[str | None, Field(max_length=500)] = None


class UserUpdate(UserPermissionFields):
    """
    Request body for PUT /api/v1/users/{id}. All fields optional.

    `password` is only re-hashed when present; leaving it out keeps the
    current password, which is what an edit dialog that does not ask for a
    new password must do.
    """

    model_config = ConfigDict(from_attributes=True)

    username: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    email: Annotated[str | None, Field(max_length=150)] = None
    password: Annotated[str | None, Field(min_length=6, max_length=72)] = None
    full_name: Annotated[str | None, Field(min_length=1, max_length=150)] = None
    role: str | None = Field(default=None, pattern=ROLE_PATTERN)
    store_id: int | None = None
    is_active: bool | None = None
    avatar_url: Annotated[str | None, Field(max_length=500)] = None

    can_edit_product: bool | None = None
    can_delete_product: bool | None = None
    can_view_report: bool | None = None
    can_manage_inventory: bool | None = None
    can_manage_order: bool | None = None
    can_manage_transfer: bool | None = None
    can_manage_user: bool | None = None


__all__ = [
    "UserCreate",
    "UserCreated",
    "UserUpdate",
    "UserRead",
    "UserPermissionFields",
]
