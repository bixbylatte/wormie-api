from pathlib import Path
from typing import Protocol
from urllib.parse import quote
from uuid import uuid4

from fastapi import UploadFile
from google.cloud import storage

from app.core.config import Settings


class CoverStorage(Protocol):
    async def save_cover(self, upload: UploadFile) -> str:
        """Persist the uploaded cover and return its object key."""

    def url_for(self, object_key: str) -> str:
        """Return a browser-safe URL for the stored object."""


class LocalCoverStorage:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_cover(self, upload: UploadFile) -> str:
        suffix = Path(upload.filename or "cover.jpg").suffix or ".jpg"
        file_name = f"{uuid4().hex}{suffix.lower()}"
        destination = self.base_dir / file_name
        content = await upload.read()
        destination.write_bytes(content)
        return file_name

    def url_for(self, object_key: str) -> str:
        return f"/media/{object_key}"


class GoogleCloudStorageCoverStorage:
    def __init__(self, bucket_name: str, public_base_url: str | None = None, client: storage.Client | None = None) -> None:
        self.bucket_name = bucket_name
        self.client = client or storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None

    async def save_cover(self, upload: UploadFile) -> str:
        suffix = Path(upload.filename or "cover.jpg").suffix or ".jpg"
        object_key = f"covers/{uuid4().hex}{suffix.lower()}"
        blob = self.bucket.blob(object_key)
        content = await upload.read()
        blob.upload_from_string(content, content_type=upload.content_type or "image/jpeg")
        return object_key

    def url_for(self, object_key: str) -> str:
        if self.public_base_url:
            return f"{self.public_base_url}/{quote(object_key, safe='/')}"
        return f"https://storage.googleapis.com/{self.bucket_name}/{quote(object_key, safe='/')}"


def build_cover_storage(settings: Settings) -> CoverStorage:
    if settings.storage_backend == "gcs":
        if not settings.gcs_bucket_name:
            raise ValueError("GCS_BUCKET_NAME is required when STORAGE_BACKEND is set to 'gcs'.")
        return GoogleCloudStorageCoverStorage(settings.gcs_bucket_name, settings.gcs_public_base_url)
    return LocalCoverStorage(settings.cover_storage_dir)
