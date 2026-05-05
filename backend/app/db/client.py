"""Supabase client factories for anon and service-role access."""

from supabase import Client, create_client

from app.core.config import get_settings


settings = get_settings()


def get_supabase_client() -> Client:
    """Creates an anon Supabase client for authentication operations.

    Returns:
        Supabase client configured with the anon key.
    """
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_supabase_admin_client() -> Client:
    """Creates a service-role Supabase client for backend-owned queries.

    Returns:
        Supabase client configured with the service role key.
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
