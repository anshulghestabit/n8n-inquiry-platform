from supabase import Client, create_client

from app.core.config import get_settings


settings = get_settings()


def get_supabase_client() -> Client:
    """Anon client: respects RLS. Use for auth operations."""
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_supabase_admin_client() -> Client:
    """Service role client: bypasses RLS after FastAPI auth gates access."""
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
