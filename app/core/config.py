from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Wormie"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./wormie.db"
    jwt_secret: str = "wormie-local-dev-secret-please-change-me-32-bytes"
    jwt_algorithm: str = "HS256"
    token_expiry_minutes: int = 60 * 24 * 7
    cover_storage_dir: Path = Field(default=Path("storage/covers"))
    storage_backend: Literal["local", "gcs"] = "local"
    gcs_bucket_name: str | None = None
    gcs_public_base_url: str | None = None
    max_upload_size_mb: int = 5
    allowed_origins: Annotated[list[str], NoDecode] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return value
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.cover_storage_dir = settings.cover_storage_dir.resolve()
    if settings.storage_backend == "local":
        settings.cover_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
