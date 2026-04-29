from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RequestStatus


class ShareRequest(Base):
    __tablename__ = "share_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("book_listings.id"), index=True)
    requester_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), default=RequestStatus.PENDING)
    requested_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    selected_offered_book_id: Mapped[int | None] = mapped_column(ForeignKey("book_listings.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    book = relationship("BookListing", foreign_keys=[book_id], back_populates="requests")
    requester = relationship("User", back_populates="requested_shares")
    offered_books = relationship("TradeRequestOffer", back_populates="request", cascade="all, delete-orphan")
    selected_offered_book = relationship("BookListing", foreign_keys=[selected_offered_book_id], back_populates="selected_in_requests")


class TradeRequestOffer(Base):
    __tablename__ = "trade_request_offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("share_requests.id"), index=True)
    offered_book_id: Mapped[int] = mapped_column(ForeignKey("book_listings.id"), index=True)

    request = relationship("ShareRequest", back_populates="offered_books")
    offered_book = relationship("BookListing", back_populates="offered_in_requests")

