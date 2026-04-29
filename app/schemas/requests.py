from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import RequestStatus, ShareMode
from app.schemas.auth import UserSummary
from app.schemas.books import BookSummary


class CreateShareRequestInput(BaseModel):
    requested_days: int | None = Field(default=None, ge=1, le=365)
    offered_book_ids: list[int] = Field(default_factory=list)


class ApproveShareRequestInput(BaseModel):
    selected_offered_book_id: int | None = None


class ShareRequestSummary(BaseModel):
    id: int
    status: RequestStatus
    share_mode: ShareMode
    requested_days: int | None
    due_date: datetime | None
    created_at: datetime
    book: BookSummary
    requester: UserSummary
    owner: UserSummary
    offered_books: list[BookSummary]
    selected_offered_book_id: int | None


class GroupedRequestsResponse(BaseModel):
    your_requests: list[ShareRequestSummary]
    requests_from_others: list[ShareRequestSummary]

