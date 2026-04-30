from app.models.book import BookListing
from app.models.share_request import ShareRequest
from app.schemas.auth import UserSummary
from app.schemas.books import BookSummary
from app.schemas.requests import ShareRequestSummary
from app.services.storage import CoverStorage


def serialize_user(user) -> UserSummary:
    return UserSummary.model_validate(user)


def serialize_book(book: BookListing, storage: CoverStorage) -> BookSummary:
    return BookSummary(
        id=book.id,
        share_mode=book.share_mode,
        status=book.status,
        max_lend_days=book.max_lend_days,
        title=book.title,
        author=book.author,
        genre=book.genre,
        details_url=book.details_url,
        cover_url=storage.url_for(book.cover_object_key),
        created_at=book.created_at,
        owner=serialize_user(book.owner),
    )


def serialize_request(share_request: ShareRequest, storage: CoverStorage) -> ShareRequestSummary:
    return ShareRequestSummary(
        id=share_request.id,
        status=share_request.status,
        share_mode=share_request.book.share_mode,
        requested_days=share_request.requested_days,
        due_date=share_request.due_date,
        created_at=share_request.created_at,
        book=serialize_book(share_request.book, storage),
        requester=serialize_user(share_request.requester),
        owner=serialize_user(share_request.book.owner),
        offered_books=[serialize_book(item.offered_book, storage) for item in share_request.offered_books],
        selected_offered_book_id=share_request.selected_offered_book_id,
    )
