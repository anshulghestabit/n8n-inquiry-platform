"""Application settings loaded from environment variables."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Runtime configuration for backend integrations and application behavior.

    Attributes:
        llm_provider: LLM backend name, such as `sarvam` or `lmstudio`.
        n8n_url: Internal URL for the n8n service.
        supabase_url: Supabase project URL.
        frontend_url: Public frontend URL used for browser redirects and CORS.
    """

    # LLM
    llm_provider: str = Field(..., min_length=1)
    sarvam_api_key: str = ""
    sarvam_base_url: str = ""
    sarvam_model: str = ""
    lm_studio_base_url: str = ""
    lm_studio_model: str = ""

    # n8n
    n8n_encryption_key: str = ""
    n8n_url: str = Field(..., min_length=1)
    n8n_api_key: str = ""
    n8n_runners_auth_token: str = ""
    n8n_callback_secret: str = ""
    demo_shared_n8n_workflow_id: str = ""
    google_sheet_id: str = ""
    google_sheet_name: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    # Supabase
    supabase_url: str = Field(..., min_length=1)
    supabase_anon_key: str = Field(..., min_length=1)
    supabase_service_role_key: str = Field(..., min_length=1)
    supabase_jwt_secret: str = ""

    # App
    secret_key: str = ""
    environment: str = Field(..., min_length=1)
    frontend_url: str = Field(..., min_length=1)
    next_public_api_url: str = ""
    auth_cookie_domain: str = ""
    auth_cookie_secure: bool = False
    backend_docs_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache()
def get_settings() -> Settings:
    """Returns a cached settings instance for dependency-free modules.

    Returns:
        Parsed application settings.
    """
    return Settings()
