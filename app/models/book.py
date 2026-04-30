from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ListingStatus, ShareMode


class BookListing(Base):
    __tablename__ = "book_listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    share_mode: Mapped[ShareMode] = mapped_column(Enum(ShareMode, name="share_mode", native_enum=False, length=32))
    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus, name="listing_status", native_enum=False, length=32),
        default=ListingStatus.AVAILABLE,
    )
    max_lend_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(120), nullable=True)
    details_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_object_key: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    owner = relationship("User", back_populates="books")
    requests = relationship("ShareRequest", back_populates="book", foreign_keys="ShareRequest.book_id")
    offered_in_requests = relationship(
        "TradeRequestOffer",
        back_populates="offered_book",
        foreign_keys="TradeRequestOffer.offered_book_id",
    )
    selected_in_requests = relationship(
        "ShareRequest",
        foreign_keys="ShareRequest.selected_offered_book_id",
        back_populates="selected_offered_book",
    )
