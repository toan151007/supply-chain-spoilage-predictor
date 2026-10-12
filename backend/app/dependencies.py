"""
Shared FastAPI dependencies: authentication and role checks (B12).

The logout denylist lives here rather than in a database table on purpose.
Adding a table means a migration, and the three seeded users plus a demo
dataset do not justify one yet. The trade-off is real and worth stating
plainly: **the denylist is per-process, so restarting the server un-revokes
every logged-out token.** For a single-process development server that is
acceptable; for a multi-process deployment it is not, and the denylist would
have to move to Redis or a table. Entries are dropped once they expire, so
the set cannot grow without bound.
"""

import threading
import time
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    TokenError,
    decode_token,
)

# auto_error=False so a missing header produces our own 401 with a clear
# message instead of FastAPI's default, and so the refresh endpoint can read
# the token from the body instead of the header.
bearer_scheme = HTTPBearer(auto_error=False)

# Roles allowed to perform a given operation, most privileged first.
ROLE_RANK = {"staff": 1, "manager": 2, "owner": 3}


class TokenDenylist:
    """JTI values that have been explicitly revoked, with their expiry."""

    def __init__(self) -> None:
        self._entries: dict[str, float] = {}
        self._lock = threading.Lock()

    def revoke(self, jti: str, expires_at: int) -> None:
        with self._lock:
            self._entries[jti] = float(expires_at)

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            self._sweep_locked()
            return jti in self._entries

    def _sweep_locked(self) -> None:
        """Drop entries whose token has already expired."""
        now = time.time()
        for jti in [k for k, exp in self._entries.items() if exp < now]:
            del self._entries[jti]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            self._sweep_locked()
            return len(self._entries)


# Module-level so every request handler sees the same set.
denylist = TokenDenylist()


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the caller from the bearer token, or raise 401.

    Re-reads the user from the database on every call rather than trusting
    the claims: a deactivated account or a changed role must stop working
    immediately, and a token issued before that change would otherwise stay
    valid until it expires.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials, expected_type=ACCESS_TOKEN_TYPE)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.reason,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    jti = payload.get("jti")
    if jti and denylist.is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked by logout",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is not a valid user id",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


def get_current_active_refresh_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> dict | None:
    """
    Resolve a refresh token from the Authorization header.

    Returns None when the header is simply absent, so the caller can fall
    back to a token in the request body. A token that IS present but
    invalid still raises, because that is a real error rather than a
    missing credential.

    Making this lenient matters: if it raised on a missing header, a client
    sending the refresh token in the body - which is the usual pattern for a
    browser holding it in an httpOnly cookie - would be rejected before the
    body was ever read.
    """
    if credentials is None or not credentials.credentials:
        return None

    try:
        payload = decode_token(
            credentials.credentials, expected_type=REFRESH_TOKEN_TYPE
        )
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.reason,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    jti = payload.get("jti")
    if jti and denylist.is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked by logout",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def require_role(*allowed: str):
    """
    Build a dependency that only lets the listed roles through.

    Returns 403 rather than 401 when the caller is authenticated but not
    permitted - the distinction matters to a client deciding whether to log
    in again or to show the user a permissions message.
    """
    wanted = set(allowed)

    def _checker(current: Annotated[User, Depends(get_current_user)]) -> User:
        if current.role not in wanted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{current.role}' cannot perform this action; "
                    f"requires one of: {sorted(wanted)}"
                ),
            )
        return current

    return _checker


# Convenience aliases so routers read clearly.
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminOnly = Annotated[User, Depends(require_role("owner"))]
ManagerOrOwner = Annotated[User, Depends(require_role("owner", "manager"))]
AnyStaff = Annotated[User, Depends(require_role("owner", "manager", "staff"))]
