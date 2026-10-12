"""
Pydantic schemas for the authentication API (B12).

`UserRead` deliberately omits `password_hash`. It carries
`from_attributes=True` so the ORM object converts directly, and the field is
simply absent from the model - which is stronger than excluding it, because
a future `UserRead` cannot accidentally start leaking it.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Mirrors the CHECK constraint on users.role. Note it is owner/manager/staff,
# not admin - "owner" is the top role in this schema.
UserRole = str


class LoginRequest(BaseModel):
    """Request body for POST /api/v1/auth/login."""

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    """
    Request body for POST /api/v1/auth/refresh.

    The refresh token may be sent here instead of the Authorization header.
    Supporting both lets a browser client keep the refresh token in an
    httpOnly cookie while a CLI client passes it explicitly.
    """

    refresh_token: str | None = None


class UserRead(BaseModel):
    """A user as returned by the API. Never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str | None
    full_name: str
    role: UserRole
    store_id: int | None
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """Successful login / refresh payload."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        description="Access token lifetime in seconds"
    )
    user: UserRead


class Message(BaseModel):
    """Simple acknowledgement body."""

    message: str
