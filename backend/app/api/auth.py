import logging

from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db.client import get_supabase_admin_client, get_supabase_client
from app.middleware.auth import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])
AUTH_COOKIE = "auth-token"
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


def api_error(status_code: int, message: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": message, "code": code},
    )


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=3600 * 24 * 7,
    )


def seed_profile_rows(db, user_id: str, email: str, full_name: str) -> None:
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


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest):
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
    response.delete_cookie(AUTH_COOKIE)
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    try:
        result = (
            db.table("profiles")
            .select("*")
            .eq("id", current_user["id"])
            .single()
            .execute()
        )
    except Exception:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "Profile not found",
            "NOT_FOUND",
        )

    return result.data


@router.put("/me")
async def update_me(
    data: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
):
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
