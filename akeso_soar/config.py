"""Application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_env: str = "development"
    app_debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://akeso:changeme_in_production@localhost:5432/akeso_soar"

    # JWT
    jwt_secret_key: str = "replace-with-a-secure-random-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Encryption
    secrets_encryption_key: str = "replace-with-fernet-key"


settings = Settings()
