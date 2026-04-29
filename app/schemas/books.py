from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ListingStatus, ShareMode
from app.schemas.auth import UserSummary


class BookSummary(BaseModel):
    id: int
    share_mode: ShareMode
    status: ListingStatus
    max_lend_days: int | None
    title: str
    author: str
    genre: str | None
    details_url: str | None
    cover_url: str
    created_at: datetime
    owner: UserSummary


class BookListResponse(BaseModel):
    items: list[BookSummary]


class BookAvailabilityInput(BaseModel):
    status: ListingStatus
