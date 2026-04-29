from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.api.serializers import serialize_request
from app.core.config import get_settings
from app.db.session import get_db
from app.models.book import BookListing
from app.models.enums import ListingStatus, RequestStatus, ShareMode
from app.models.share_request import ShareRequest, TradeRequestOffer
from app.models.user import User
from app.schemas.requests import ApproveShareRequestInput, CreateShareRequestInput, GroupedRequestsResponse, ShareRequestSummary
from app.services.storage import LocalCoverStorage

router = APIRouter(prefix="/requests", tags=["requests"])
storage = LocalCoverStorage(get_settings().cover_storage_dir)


def _request_query():
    return (
        select(ShareRequest)
        .options(
            joinedload(ShareRequest.requester),
            joinedload(ShareRequest.book).joinedload(BookListing.owner),
            joinedload(ShareRequest.offered_books).joinedload(TradeRequestOffer.offered_book).joinedload(BookListing.owner),
        )
    )


@router.post("/books/{book_id}", response_model=ShareRequestSummary, status_code=status.HTTP_201_CREATED)
def create_share_request(
    book_id: int,
    payload: CreateShareRequestInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShareRequestSummary:
    book = db.scalar(select(BookListing).options(joinedload(BookListing.owner)).where(BookListing.id == book_id))
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found.")
    if book.owner_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot request your own book.")
    if book.status != ListingStatus.AVAILABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This book is not available right now.")

    share_request = ShareRequest(book_id=book.id, requester_user_id=current_user.id)
    db.add(share_request)
    db.flush()

    if book.share_mode == ShareMode.LEND:
        if payload.requested_days is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Please provide the number of days you need for a lend request.")
        if book.max_lend_days is not None and payload.requested_days > book.max_lend_days:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"This listing can only be lent for up to {book.max_lend_days} days.",
            )
        share_request.requested_days = payload.requested_days
    else:
        if not payload.offered_book_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Trade requests need at least one offered book.")
        offered_books = db.scalars(
            select(BookListing).options(joinedload(BookListing.owner)).where(BookListing.id.in_(payload.offered_book_ids))
        ).all()
        if len(offered_books) != len(set(payload.offered_book_ids)):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="One or more offered books do not exist.")

        for offered_book in offered_books:
            if offered_book.owner_user_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only offer your own books.")
            if offered_book.share_mode != ShareMode.TRADE or offered_book.status != ListingStatus.AVAILABLE:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="All offered books must be available trade listings.")
            db.add(TradeRequestOffer(request_id=share_request.id, offered_book_id=offered_book.id))

    db.commit()
    result = db.scalar(_request_query().where(ShareRequest.id == share_request.id))
    return serialize_request(result, storage)


@router.get("", response_model=GroupedRequestsResponse)
def list_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupedRequestsResponse:
    outgoing = db.scalars(_request_query().where(ShareRequest.requester_user_id == current_user.id)).unique().all()
    incoming = db.scalars(
        _request_query().where(ShareRequest.book_id.in_(select(BookListing.id).where(BookListing.owner_user_id == current_user.id)))
    ).unique().all()
    return GroupedRequestsResponse(
        your_requests=[serialize_request(item, storage) for item in outgoing],
        requests_from_others=[serialize_request(item, storage) for item in incoming],
    )


def _load_request_for_owner(db: Session, request_id: int, owner_id: int) -> ShareRequest:
    share_request = db.scalar(_request_query().where(ShareRequest.id == request_id))
    if share_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    if share_request.book.owner_user_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage requests for your own books.")
    return share_request


@router.post("/{request_id}/approve", response_model=ShareRequestSummary)
def approve_request(
    request_id: int,
    payload: ApproveShareRequestInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShareRequestSummary:
    share_request = _load_request_for_owner(db, request_id, current_user.id)
    if share_request.status != RequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending requests can be approved.")
    if share_request.book.status != ListingStatus.AVAILABLE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This book is no longer available.")

    selected_book: BookListing | None = None
    if share_request.book.share_mode == ShareMode.TRADE:
        offered_book_ids = [item.offered_book_id for item in share_request.offered_books]
        if payload.selected_offered_book_id not in offered_book_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choose one of the offered books to complete the trade.")
        selected_book = db.get(BookListing, payload.selected_offered_book_id)
        if selected_book is None or selected_book.status != ListingStatus.AVAILABLE:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That offered book is no longer available.")
        selected_book.status = ListingStatus.UNAVAILABLE
        share_request.selected_offered_book_id = selected_book.id
    else:
        share_request.due_date = datetime.now(UTC) + timedelta(days=share_request.requested_days or 0)

    share_request.status = RequestStatus.APPROVED
    share_request.book.status = ListingStatus.UNAVAILABLE

    request_filters = [ShareRequest.book_id == share_request.book_id]
    if selected_book is not None:
        request_filters.append(ShareRequest.book_id == selected_book.id)

    other_requests = db.scalars(
        select(ShareRequest).where(
            or_(*request_filters),
            ShareRequest.id != share_request.id,
            ShareRequest.status == RequestStatus.PENDING,
        )
    ).all()
    for pending_request in other_requests:
        pending_request.status = RequestStatus.REJECTED

    db.commit()
    refreshed = db.scalar(_request_query().where(ShareRequest.id == share_request.id))
    return serialize_request(refreshed, storage)


@router.post("/{request_id}/reject", response_model=ShareRequestSummary)
def reject_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShareRequestSummary:
    share_request = _load_request_for_owner(db, request_id, current_user.id)
    if share_request.status != RequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending requests can be rejected.")
    share_request.status = RequestStatus.REJECTED
    db.commit()
    refreshed = db.scalar(_request_query().where(ShareRequest.id == share_request.id))
    return serialize_request(refreshed, storage)


@router.post("/{request_id}/return", response_model=ShareRequestSummary)
def return_lend(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShareRequestSummary:
    share_request = _load_request_for_owner(db, request_id, current_user.id)
    if share_request.book.share_mode != ShareMode.LEND or share_request.status != RequestStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only approved lend requests can be returned.")
    share_request.status = RequestStatus.RETURNED
    share_request.book.status = ListingStatus.AVAILABLE
    db.commit()
    refreshed = db.scalar(_request_query().where(ShareRequest.id == share_request.id))
    return serialize_request(refreshed, storage)


@router.post("/{request_id}/complete", response_model=ShareRequestSummary)
def complete_trade(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShareRequestSummary:
    share_request = _load_request_for_owner(db, request_id, current_user.id)
    if share_request.book.share_mode != ShareMode.TRADE or share_request.status != RequestStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only approved trade requests can be completed.")
    if share_request.selected_offered_book is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This trade does not have an accepted offered book.")

    share_request.status = RequestStatus.COMPLETED
    share_request.book.status = ListingStatus.ARCHIVED
    share_request.selected_offered_book.status = ListingStatus.ARCHIVED
    db.commit()
    refreshed = db.scalar(_request_query().where(ShareRequest.id == share_request.id))
    return serialize_request(refreshed, storage)
