from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # LLM
    llm_provider: str = "sarvam"
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai/v1"
    sarvam_model: str = "sarvam-30b"
    lm_studio_base_url: str = "http://host.docker.internal:1234/v1"
    lm_studio_model: str = "local-model"

    # n8n
    n8n_url: str = "http://n8n:5678"
    n8n_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # App
    secret_key: str = ""
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()