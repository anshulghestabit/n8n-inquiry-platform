"""Authentication and profile API routes backed by Supabase Auth."""

import logging

from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db.client import get_supabase_admin_client, get_supabase_client
from app.core.config import get_settings
from app.middleware.auth import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])
AUTH_COOKIE = "auth-token"
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    """Request body for creating a new Supabase user and profile."""

    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""


class LoginRequest(BaseModel):
    """Request body for password-based login."""

    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    """Request body for mutable profile fields."""

    full_name: str | None = None
    avatar_url: str | None = None


def api_error(status_code: int, message: str, code: str) -> HTTPException:
    """Builds a normalized API error response.

    Args:
        status_code: HTTP status code for the response.
        message: Human-readable error message.
        code: Machine-readable error code.

    Returns:
        HTTP exception carrying the standard error envelope.
    """
    return HTTPException(
        status_code=status_code,
        detail={"error": message, "code": code},
    )


def set_auth_cookie(response: Response, token: str) -> None:
    """Stores a Supabase access token in an httpOnly browser cookie.

    Args:
        response: FastAPI response to mutate.
        token: Supabase access token.
    """
    settings = get_settings()
    cookie_domain = settings.auth_cookie_domain or None

    response.set_cookie(
        key=AUTH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=3600 * 24 * 7,
        domain=cookie_domain,
    )


def seed_profile_rows(db, user_id: str, email: str, full_name: str) -> None:
    """Creates or repairs app-owned rows for a newly registered user.

    Args:
        db: Supabase service-role client.
        user_id: Supabase Auth user ID.
        email: Registered email address.
        full_name: Optional display name.
    """
    db.table("profiles").upsert(
        {
            "id": user_id,
            "email": email,
            "full_name": full_name,
        },
        on_conflict="id",
    ).execute()

    db.table("data_sources").upsert(
        [
            {"user_id": user_id, "source_type": "gmail", "is_connected": False},
            {"user_id": user_id, "source_type": "telegram", "is_connected": False},
            {"user_id": user_id, "source_type": "google_drive", "is_connected": False},
            {"user_id": user_id, "source_type": "google_sheets", "is_connected": False},
        ],
        on_conflict="user_id,source_type",
    ).execute()


def fetch_profile_row(db, user_id: str) -> dict | None:
    """Fetches one profile row without raising when it is missing.

    Args:
        db: Supabase service-role client.
        user_id: Supabase Auth user ID.

    Returns:
        Profile row when present, otherwise `None`.
    """
    result = (
        db.table("profiles")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def profile_response(profile: dict, current_user: dict) -> dict:
    """Normalizes a profile response with the verified auth email fallback.

    Args:
        profile: Profile row from Supabase.
        current_user: Authenticated user payload.

    Returns:
        Profile row suitable for frontend auth state.
    """
    email = current_user.get("email")
    if email and not profile.get("email"):
        return {**profile, "email": email}
    return profile


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest):
    """Creates a Supabase Auth user and seeds application profile rows."""
    sb = get_supabase_admin_client()
    try:
        result = sb.auth.admin.create_user(
            {
                "email": str(data.email),
                "password": data.password,
                "email_confirm": True,
                "user_metadata": {"full_name": data.full_name},
            }
        )
    except Exception as exc:
        error_text = str(exc).lower()
        if "already" in error_text or "registered" in error_text or "exists" in error_text:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "Email already exists",
                "EMAIL_EXISTS",
            )
        logger.exception("Supabase registration failed")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Registration failed",
            "REGISTRATION_FAILED",
        )

    if result.user is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "Email already exists",
            "EMAIL_EXISTS",
        )

    try:
        seed_profile_rows(
            sb,
            str(result.user.id),
            str(data.email),
            data.full_name,
        )
    except Exception:
        logger.exception("Failed to seed profile rows after Supabase registration")
        try:
            sb.auth.admin.delete_user(str(result.user.id))
        except Exception:
            logger.exception("Failed to rollback Supabase auth user after profile seed failure")
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Profile setup failed",
            "PROFILE_SETUP_FAILED",
        )

    return {"message": "User created"}


@router.post("/login")
async def login(data: LoginRequest, response: Response):
    """Authenticates credentials and sets the session cookie."""
    sb = get_supabase_client()
    try:
        result = sb.auth.sign_in_with_password(
            {"email": str(data.email), "password": data.password}
        )
    except Exception:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid credentials",
            "INVALID_CREDENTIALS",
        )

    if result.session is None or not result.session.access_token:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid credentials",
            "INVALID_CREDENTIALS",
        )

    set_auth_cookie(response, result.session.access_token)
    return {
        "message": "Login successful",
        "user": {"id": str(result.user.id), "email": result.user.email},
    }


@router.post("/logout")
async def logout(response: Response):
    """Clears the session cookie used by the frontend."""
    settings = get_settings()
    response.delete_cookie(AUTH_COOKIE, domain=settings.auth_cookie_domain or None)
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Returns the current profile, repairing missing profile rows when possible."""
    db = get_supabase_admin_client()
    try:
        profile = fetch_profile_row(db, current_user["id"])
    except Exception:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Database query failed",
            "DB_ERROR",
        )

    if profile:
        return profile_response(profile, current_user)

    email = current_user.get("email")
    if not email:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "Profile not found",
            "NOT_FOUND",
        )

    try:
        seed_profile_rows(db, current_user["id"], email, "")
        profile = fetch_profile_row(db, current_user["id"])
    except Exception:
        logger.exception("Failed to repair missing profile row for authenticated user")
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Profile setup failed",
            "PROFILE_SETUP_FAILED",
        )

    if profile:
        return profile_response(profile, current_user)

    raise api_error(
        status.HTTP_404_NOT_FOUND,
        "Profile not found",
        "NOT_FOUND",
    )


@router.put("/me")
async def update_me(
    data: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
):
    """Updates mutable profile fields for the authenticated user."""
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        return await me(current_user)

    db = get_supabase_admin_client()
    try:
        result = (
            db.table("profiles")
            .update(update_data)
            .eq("id", current_user["id"])
            .execute()
        )
    except Exception:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Database query failed",
            "DB_ERROR",
        )

    if not result.data:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "Profile not found",
            "NOT_FOUND",
        )

    return result.data[0]
