"""FastAPI authentication dependency for Supabase-issued JWTs."""

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.client import get_supabase_client


security = HTTPBearer(auto_error=False)
INVALID_TOKEN_MESSAGE = "Invalid token"
TOKEN_EXPIRED_MESSAGE = "Token expired"


class TokenExpiredError(Exception):
    """Raised when Supabase reports an expired access token."""


class TokenValidationError(Exception):
    """Raised when Supabase cannot validate an access token."""


def auth_error(message: str, code: str) -> HTTPException:
    """Builds a normalized 401 authentication error.

    Args:
        message: Human-readable error message.
        code: Machine-readable error code.

    Returns:
        HTTP exception with the standard auth error envelope.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": message, "code": code},
    )


def validate_token_with_supabase(token: str) -> dict:
    """Validates a Supabase access token through Supabase Auth.

    Args:
        token: Supabase access token.

    Returns:
        Minimal auth payload containing `sub` and `email`.

    Raises:
        TokenExpiredError: If Supabase reports token expiry.
        TokenValidationError: If Supabase cannot validate the token.
    """
    try:
        response = get_supabase_client().auth.get_user(token)
    except Exception as exc:
        if "expired" in str(exc).lower():
            raise TokenExpiredError(TOKEN_EXPIRED_MESSAGE) from exc
        raise TokenValidationError("Supabase token validation failed") from exc

    user = getattr(response, "user", None)
    if user is None:
        raise TokenValidationError("Supabase token validation returned no user")

    return {
        "sub": str(user.id),
        "email": user.email,
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_token: str | None = Cookie(default=None, alias="auth-token"),
) -> dict:
    """Resolves the authenticated user from bearer credentials or cookie.

    Args:
        credentials: Optional Authorization bearer credentials.
        auth_token: Optional `auth-token` cookie value.

    Returns:
        Current user identity with `id` and `email`.

    Raises:
        HTTPException: If the request is unauthenticated or token validation fails.
    """
    token = credentials.credentials if credentials else auth_token
    if not token:
        raise auth_error(INVALID_TOKEN_MESSAGE, "INVALID_TOKEN")

    try:
        payload = validate_token_with_supabase(token)
    except TokenExpiredError:
        raise auth_error(TOKEN_EXPIRED_MESSAGE, "TOKEN_EXPIRED")
    except TokenValidationError:
        raise auth_error(INVALID_TOKEN_MESSAGE, "INVALID_TOKEN")

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id:
        raise auth_error(INVALID_TOKEN_MESSAGE, "INVALID_TOKEN")

    return {"id": user_id, "email": email}
