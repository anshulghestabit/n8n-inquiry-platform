from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.core.config import get_settings
from app.db.client import get_supabase_client


settings = get_settings()
security = HTTPBearer(auto_error=False)
_jwks_cache: dict[str, dict] = {}
_ASYMMETRIC_ALGORITHMS = ["RS256"]


def auth_error(message: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": message, "code": code},
    )


async def get_jwk(kid: str) -> dict | None:
    if kid in _jwks_cache:
        return _jwks_cache[kid]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
                timeout=5.0,
            )
            response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise JWTError("Supabase JWK lookup failed") from exc

    if not isinstance(payload, dict):
        raise JWTError("Supabase JWK lookup returned invalid payload")

    for key in payload.get("keys", []):
        if key.get("kid"):
            _jwks_cache[key["kid"]] = key

    return _jwks_cache.get(kid)


async def decode_supabase_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    if settings.supabase_jwt_secret:
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except JWTError:
            pass

    key = await get_jwk(header.get("kid", ""))
    if key is None:
        raise JWTError("No matching Supabase JWK found")

    algorithm = header.get("alg")
    if algorithm and algorithm not in _ASYMMETRIC_ALGORITHMS:
        raise JWTError("Unsupported Supabase signing algorithm")

    return jwt.decode(
        token,
        key,
        algorithms=_ASYMMETRIC_ALGORITHMS,
        options={"verify_aud": False},
    )


def validate_token_with_supabase(token: str) -> dict:
    try:
        response = get_supabase_client().auth.get_user(token)
    except Exception as exc:
        if "expired" in str(exc).lower():
            raise ExpiredSignatureError("Token expired") from exc
        raise JWTError("Supabase token validation failed") from exc

    user = getattr(response, "user", None)
    if user is None:
        raise JWTError("Supabase token validation returned no user")

    return {
        "sub": str(user.id),
        "email": user.email,
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_token: str | None = Cookie(default=None, alias="auth-token"),
) -> dict:
    token = credentials.credentials if credentials else auth_token
    if not token:
        raise auth_error("Invalid token", "INVALID_TOKEN")

    try:
        payload = await decode_supabase_token(token)
    except ExpiredSignatureError:
        raise auth_error("Token expired", "TOKEN_EXPIRED")
    except JWTError:
        try:
            payload = validate_token_with_supabase(token)
        except ExpiredSignatureError:
            raise auth_error("Token expired", "TOKEN_EXPIRED")
        except JWTError:
            raise auth_error("Invalid token", "INVALID_TOKEN")

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id:
        raise auth_error("Invalid token", "INVALID_TOKEN")

    return {"id": user_id, "email": email}
