from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.api.serializers import serialize_book
from app.core.config import get_settings
from app.db.session import get_db
from app.models.book import BookListing
from app.models.enums import ListingStatus, RequestStatus, ShareMode
from app.models.share_request import ShareRequest
from app.models.user import User
from app.schemas.books import BookAvailabilityInput, BookListResponse, BookSummary
from app.services.storage import LocalCoverStorage

router = APIRouter(prefix="/books", tags=["books"])
settings = get_settings()
storage = LocalCoverStorage(settings.cover_storage_dir)


@router.get("", response_model=BookListResponse)
def list_books(
    include_unavailable: bool = Query(default=False),
    mine_only: bool = Query(default=False),
    share_mode: ShareMode | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookListResponse:
    query = select(BookListing).options(joinedload(BookListing.owner)).order_by(desc(BookListing.created_at))

    if not include_unavailable:
        query = query.where(BookListing.status == ListingStatus.AVAILABLE)
    if mine_only:
        query = query.where(BookListing.owner_user_id == current_user.id)
    if share_mode is not None:
        query = query.where(BookListing.share_mode == share_mode)

    books = db.scalars(query).unique().all()
    return BookListResponse(items=[serialize_book(book, storage) for book in books])


@router.get("/{book_id}", response_model=BookSummary)
def get_book(book_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> BookSummary:
    book = db.scalar(select(BookListing).options(joinedload(BookListing.owner)).where(BookListing.id == book_id))
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found.")
    return serialize_book(book, storage)


@router.post("", response_model=BookSummary, status_code=status.HTTP_201_CREATED)
async def create_book(
    share_mode: ShareMode = Form(...),
    title: str = Form(..., min_length=1, max_length=255),
    author: str = Form(..., min_length=1, max_length=255),
    genre: str | None = Form(default=None),
    details_url: str | None = Form(default=None),
    max_lend_days: int | None = Form(default=None),
    cover: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookSummary:
    if share_mode == ShareMode.LEND and (max_lend_days is None or max_lend_days < 1):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lend listings require a maximum number of days.")
    if share_mode == ShareMode.TRADE:
        max_lend_days = None

    file_name = await storage.save_cover(cover)
    book = BookListing(
        owner_user_id=current_user.id,
        share_mode=share_mode,
        status=ListingStatus.AVAILABLE,
        max_lend_days=max_lend_days,
        title=title.strip(),
        author=author.strip(),
        genre=genre.strip() if genre else None,
        details_url=details_url.strip() if details_url else None,
        cover_object_key=file_name,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    db.refresh(current_user)
    book.owner = current_user
    return serialize_book(book, storage)


@router.patch("/{book_id}/availability", response_model=BookSummary)
def update_availability(
    book_id: int,
    payload: BookAvailabilityInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookSummary:
    if payload.status not in {ListingStatus.AVAILABLE, ListingStatus.UNAVAILABLE}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Only available and unavailable states can be set manually.")

    book = db.scalar(select(BookListing).options(joinedload(BookListing.owner)).where(BookListing.id == book_id))
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found.")
    if book.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own books.")

    active_approved_request = db.scalar(
        select(ShareRequest.id).where(
            ShareRequest.status == RequestStatus.APPROVED,
            (ShareRequest.book_id == book.id) | (ShareRequest.selected_offered_book_id == book.id),
        )
    )
    if active_approved_request:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This book already has an active approved request.")

    book.status = payload.status
    db.commit()
    db.refresh(book)
    return serialize_book(book, storage)
