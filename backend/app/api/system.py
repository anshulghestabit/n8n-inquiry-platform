import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.db.client import get_supabase_admin_client
from app.middleware.auth import get_current_user


router = APIRouter(prefix="/system", tags=["system"])
settings = get_settings()


@router.get("/status")
async def system_status(current_user: dict = Depends(get_current_user)):
    connection_status = {
        "n8n": False,
        "gmail": False,
        "whatsapp": False,
        "google_drive": False,
        "google_sheets": False,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.n8n_url}/api/v1/workflows",
                headers={"X-N8N-API-KEY": settings.n8n_api_key},
                timeout=3.0,
            )
            connection_status["n8n"] = response.status_code == 200
    except Exception:
        connection_status["n8n"] = False

    try:
        db = get_supabase_admin_client()
        sources = (
            db.table("data_sources")
            .select("source_type, is_connected")
            .eq("user_id", current_user["id"])
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Database query failed", "code": "DB_ERROR"},
        )

    for row in sources.data or []:
        source_type = row.get("source_type")
        if source_type in connection_status:
            connection_status[source_type] = bool(row.get("is_connected"))

    return connection_status
