"""
Password hashing and JWT helpers (B12).

Two deliberate choices here, both forced by real behaviour rather than
preference.

1. `bcrypt` is used DIRECTLY, not through passlib.
   passlib 1.7.4 reads `bcrypt.__about__.__version__`, an attribute removed
   in bcrypt 4.1+. With the bcrypt 5.0 installed here, passlib swallows the
   AttributeError and then reports
       ValueError: password cannot be longer than 72 bytes
   for a 7-byte password. The message is simply wrong and would send you
   hunting for a non-existent problem. The bcrypt library itself is
   unaffected, so the wrapper is what gets dropped.

2. Tokens carry an explicit `type` claim.
   Without it an access token would be accepted at the refresh endpoint and
   vice versa, which defeats the point of having two lifetimes. `decode`
   checks the claim so the two are not interchangeable.

Nothing in this module reads the database; `app/dependencies.py` does that.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

# bcrypt silently ignores anything past 72 bytes, so a long passphrase would
# be truncated without telling anyone. Reject instead of pretending.
MAX_PASSWORD_BYTES = 72


# ===========================================================================
# Password hashing
# ===========================================================================
def hash_password(password: str) -> str:
    """
    Hash a password with bcrypt.

    bcrypt has a hard 72-byte input limit. Silently truncating would mean
    `longpassword...A` and `longpassword...B` authenticate as the same user,
    so an over-long password is rejected outright.
    """
    if not password:
        raise ValueError("Password must not be empty")
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes when UTF-8 "
            f"encoded (got {len(encoded)})"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Check a password against a stored hash.

    Returns False rather than raising for a malformed hash: a corrupt row in
    the database should fail the login, not 500 the whole auth endpoint.
    """
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        # Includes the "invalid salt" error bcrypt raises for a value that
        # is not a hash at all - which is exactly the case for the
        # placeholder value the seeded users originally carried.
        return False


def is_placeholder_hash(password_hash: str | None) -> bool:
    """
    True when the stored value is not a real hash.

    The three seeded users shipped with a literal
    'PLACEHOLDER_NOT_A_REAL_HASH' string. Detecting that lets the login
    endpoint return an actionable message instead of a bare 401, which would
    look like a wrong password when in fact no password can ever match.
    """
    if not password_hash:
        return True
    # A real bcrypt hash is 60 characters and starts with $2b$/$2a$/$2y$.
    return not (
        len(password_hash) == 60
        and password_hash.startswith(("$2a$", "$2b$", "$2y$"))
    )


# ===========================================================================
# JWT
# ===========================================================================
def _create_token(subject: str, token_type: str, expires_delta: timedelta,
                  extra_claims: dict | None = None) -> str:
    """
    Build a signed JWT.

    `jti` gives every token a unique id, which is what makes logout able to
    revoke a specific token instead of invalidating the user's whole
    session. `sub` carries the user_id as a string because the JWT spec
    requires `sub` to be a string.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


def create_access_token(user_id: int, role: str) -> str:
    """Short-lived token for calling the API."""
    return _create_token(
        subject=str(user_id),
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"role": role},
    )


def create_refresh_token(user_id: int) -> str:
    """Long-lived token, accepted only at the refresh endpoint."""
    return _create_token(
        subject=str(user_id),
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


class TokenError(Exception):
    """Raised when a token cannot be trusted. Carries a user-facing reason."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """
    Verify a JWT and return its claims.

    Checks the signature and expiry, then the `type` claim when the caller
    says which kind of token it expected. Raises TokenError with a reason
    that is safe to show a client - never the token itself and never the key.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as exc:
        # JWTError covers expired, malformed, wrong signature and bad
        # algorithm. The text differs per case but none of it should be
        # echoed back verbatim.
        name = type(exc).__name__
        if name == "ExpiredSignatureError":
            raise TokenError("Token has expired") from exc
        raise TokenError("Token is invalid") from exc

    if expected_type and payload.get("type") != expected_type:
        raise TokenError(
            f"Expected a {expected_type} token but received a "
            f"{payload.get('type') or 'typeless'} token"
        )

    if not payload.get("sub"):
        raise TokenError("Token has no subject")

    return payload
