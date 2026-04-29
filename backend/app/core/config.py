from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # LLM
    llm_provider: str = "sarvam"
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai/v1"
    sarvam_model: str = "sarvam-105b"
    lm_studio_base_url: str = "http://host.docker.internal:1234/v1"
    lm_studio_model: str = "local-model"

    # n8n
    n8n_encryption_key: str = ""
    n8n_url: str = "http://n8n:5678"
    n8n_api_key: str = ""
    n8n_runners_auth_token: str = ""
    google_sheet_id: str = ""
    google_sheet_name: str = "Sheet1"
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # App
    secret_key: str = ""
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"
    next_public_api_url: str = "http://localhost:8000"
    auth_cookie_domain: str = ""
    auth_cookie_secure: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
