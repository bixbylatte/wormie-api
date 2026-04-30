from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.api.serializers import serialize_book
from app.core.config import Settings
from app.models.book import BookListing
from app.models.enums import ListingStatus, ShareMode
from app.models.user import User
from app.services.storage import GoogleCloudStorageCoverStorage, LocalCoverStorage


class DummyStorageClient:
    def bucket(self, _bucket_name: str) -> object:
        return object()


def test_local_storage_urls_stay_relative_for_dev(tmp_path: Path) -> None:
    storage = LocalCoverStorage(tmp_path)

    assert storage.url_for("cover.avif") == "/media/cover.avif"


def test_gcs_storage_urls_are_absolute() -> None:
    storage = GoogleCloudStorageCoverStorage("wormie-covers", client=DummyStorageClient())

    assert storage.url_for("covers/cover.avif") == "https://storage.googleapis.com/wormie-covers/covers/cover.avif"


def test_gcs_storage_urls_ignore_custom_public_base() -> None:
    storage = GoogleCloudStorageCoverStorage(
        "wormie-covers",
        public_base_url="https://cdn.example.com",
        client=DummyStorageClient(),
    )

    assert storage.url_for("covers/cover.avif") == "https://storage.googleapis.com/wormie-covers/covers/cover.avif"


def test_gcs_public_base_url_must_be_absolute() -> None:
    with pytest.raises(ValueError, match="GCS_PUBLIC_BASE_URL must be an absolute http or https URL."):
        Settings(storage_backend="gcs", gcs_bucket_name="wormie-covers", gcs_public_base_url="/media")


def test_local_storage_is_rejected_for_public_https_origins() -> None:
    with pytest.raises(ValueError, match="Local storage cannot be used when public HTTPS origins are configured."):
        Settings(
            storage_backend="local",
            allowed_origins="http://127.0.0.1:5173,https://wormie-web-723556890359.asia-east1.run.app",
        )


def test_serialize_book_uses_public_gcs_url_for_cover() -> None:
    owner = User(
        id=1,
        display_name="Owner",
        email="owner@example.com",
        password_hash="hashed-password",
    )
    book = BookListing(
        id=1,
        owner_user_id=owner.id,
        owner=owner,
        share_mode=ShareMode.LEND,
        status=ListingStatus.AVAILABLE,
        max_lend_days=14,
        title="Designing Data-Intensive Applications",
        author="Martin Kleppmann",
        genre="Technology",
        details_url="https://example.com/book",
        cover_object_key="covers/cover.avif",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    summary = serialize_book(book, GoogleCloudStorageCoverStorage("wormie-covers", client=DummyStorageClient()))

    assert summary.cover_url == "https://storage.googleapis.com/wormie-covers/covers/cover.avif"
