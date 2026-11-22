from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    app_name: str = "AI Study Assistant"
    environment: str = "development"
    database_url: str = "sqlite:///./study_assistant.db"
    gemini_api_key: str = ""
    jwt_secret: str = "dev-only-change-this-secret-before-deployment"
    access_token_minutes: int = 60
    secure_cookies: bool = False
    upload_dir: str = "data/uploads"
    max_upload_mb: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
