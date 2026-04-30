from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


LOCAL_HOSTNAMES = {"127.0.0.1", "::1", "localhost"}


def is_absolute_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_public_https_origin(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname not in LOCAL_HOSTNAMES and bool(parsed.netloc)


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

    @field_validator("gcs_public_base_url")
    @classmethod
    def validate_gcs_public_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None
        if not is_absolute_http_url(normalized):
            raise ValueError("GCS_PUBLIC_BASE_URL must be an absolute http or https URL.")
        return normalized

    @model_validator(mode="after")
    def validate_storage_backend(self) -> "Settings":
        if self.storage_backend == "local" and any(is_public_https_origin(origin) for origin in self.allowed_origins):
            raise ValueError("Local storage cannot be used when public HTTPS origins are configured. Set STORAGE_BACKEND=gcs.")
        return self


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.cover_storage_dir = settings.cover_storage_dir.resolve()
    if settings.storage_backend == "local":
        settings.cover_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
