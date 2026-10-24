"""
Authentication endpoints (B12 / B3): login, refresh, me, logout,
change-password.

All database access goes through `EXEC dbo.sp_Users_*`; there is no ORM
query in this file.

Two things worth knowing before reading the code.

The three seeded users ship with a placeholder `password_hash` in some
setups, not a real hash. `is_placeholder_hash` detects that case and returns
an explicit message telling the operator to run the reset script. That is the
difference between "your password is wrong" and "this account has never had
a password set", which is the difference between a user being able to fix it
and being stuck.

Logout revokes the presented token by adding its `jti` to an in-process
denylist. A JWT cannot be un-signed, so that indirection is the standard
way to make logout mean something. See `app/dependencies.py` for why the
denylist is not in the database and what that costs.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pyodbc import Error as PyodbcError

from app.config import settings
from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import (
    CurrentUser,
    denylist,
    get_current_active_refresh_token,
    load_user,
)
from app.schemas.auth_schema import (
    LoginRequest,
    Message,
    RefreshRequest,
    TokenResponse,
    UserRead,
)
from app.security import (
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    is_placeholder_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

HTTP_422_UNPROCESSABLE_CONTENT = 422

# Reused by /logout, which needs the raw token to find its `jti` - the
# authenticated user alone is not enough to revoke a specific token.
bearer_scheme = HTTPBearer(auto_error=False)


def _load_user_by_name(db: DbSession, username: str) -> dict | None:
    return db.one("sp_Users_GetByUsername", {"Username": username})


def _issue_tokens(user: dict) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user["user_id"], user["role"]),
        refresh_token=create_refresh_token(user["user_id"]),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserRead.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse, summary="Exchange credentials for tokens")
def login(payload: LoginRequest, db: DbSession = Depends(get_db)) -> TokenResponse:
    """
    Authenticate and return an access + refresh token pair.

    A wrong username and a wrong password produce the same 401 with the same
    message. Distinguishing them would tell an attacker which usernames
    exist, and the caller gains nothing from knowing which half was wrong.

    Deactivated accounts get 403: the credentials were correct, so this is
    not an authentication failure.
    """
    try:
        user = _load_user_by_name(db, payload.username)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Credentials were valid but the account can never work. Say so instead
    # of pretending the password was wrong.
    if is_placeholder_hash(user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Account '{user['username']}' has no usable password hash "
                "(seeded placeholder). Run scripts/reset_user_passwords.py "
                "to set real passwords."
            ),
        )

    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse, summary="Mint a new access token")
def refresh(
    payload: RefreshRequest | None = None,
    db: DbSession = Depends(get_db),
    header_claims: dict | None = Depends(get_current_active_refresh_token),
) -> TokenResponse:
    """
    Exchange a refresh token for a fresh token pair.

    The token is read from the body when present, otherwise from the
    Authorization header, so a browser holding it in an httpOnly cookie and
    a CLI client passing it explicitly both work. Both paths insist on
    `type == "refresh"`, so an access token cannot be used here.

    Both tokens are reissued and the old refresh token is revoked. Without
    that, a captured refresh token would stay usable until it expired on its
    own, which defeats the point of rotating them.
    """
    token = (payload.refresh_token if payload else None)

    if token:
        try:
            claims = decode_token(token, expected_type=REFRESH_TOKEN_TYPE)
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=exc.reason,
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if claims.get("jti") and denylist.is_revoked(claims["jti"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    elif header_claims is not None:
        claims = header_claims
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "No refresh token supplied. Send it in the Authorization "
                "header as 'Bearer <token>' or in the body as "
                "{'refresh_token': '...'}."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(claims["sub"])
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token subject is not a valid user id",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        user = load_user(db, user_id)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
        )

    # Rotate: revoke the refresh token that was just used.
    jti = claims.get("jti")
    if jti:
        denylist.revoke(jti, int(claims.get("exp", 0)))

    return _issue_tokens(user)


@router.get("/me", response_model=UserRead, summary="Return the authenticated user")
def me(current: CurrentUser) -> UserRead:
    """
    Return the caller's own record.

    The user is re-read from the database by `get_current_user`, so a
    deactivated account or a changed role is reflected immediately rather
    than at token expiry.
    """
    return UserRead.model_validate(current)


@router.post("/logout", response_model=Message, summary="Revoke the current token")
def logout(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    current: CurrentUser,
) -> Message:
    """
    Revoke the presented access token.

    Stateless JWTs cannot really be logged out, so the token's `jti` is
    added to a denylist that `get_current_user` consults. See
    `app/dependencies.py` for the limitation: the denylist is per-process
    and does not survive a restart.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_token(
            credentials.credentials, expected_type="access"
        )
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.reason,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    jti = claims.get("jti")
    if jti:
        denylist.revoke(jti, int(claims.get("exp", 0)))

    return Message(message="Logged out; this token is no longer valid")


@router.post("/change-password", response_model=Message, summary="Change your own password")
def change_password(
    current: CurrentUser,
    payload: LoginRequest,
    db: DbSession = Depends(get_db),
) -> Message:
    """
    Replace the caller's own password.

    Reuses `LoginRequest` for the body: it carries exactly the two fields
    needed (`username` is ignored in favour of the authenticated identity,
    `password` is the new value).
    """
    if not verify_password(payload.password, current["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as the current one",
        )

    try:
        new_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    try:
        db.call(
            "sp_Users_ChangePassword",
            {"UserId": current["user_id"], "NewPasswordHash": new_hash},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    # Force other sessions to log in again with the new credentials.
    denylist.clear()
    return Message(message="Password changed; all tokens revoked")
