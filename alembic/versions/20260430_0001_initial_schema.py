"""Initial Wormie schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260430_0001"
down_revision = None
branch_labels = None
depends_on = None


share_mode_enum = sa.Enum("TRADE", "LEND", name="share_mode", native_enum=False, length=32)
listing_status_enum = sa.Enum(
    "AVAILABLE",
    "UNAVAILABLE",
    "ARCHIVED",
    name="listing_status",
    native_enum=False,
    length=32,
)
request_status_enum = sa.Enum(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "RETURNED",
    "COMPLETED",
    name="request_status",
    native_enum=False,
    length=32,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "book_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("share_mode", share_mode_enum, nullable=False),
        sa.Column("status", listing_status_enum, nullable=False),
        sa.Column("max_lend_days", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("genre", sa.String(length=120), nullable=True),
        sa.Column("details_url", sa.Text(), nullable=True),
        sa.Column("cover_object_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_book_listings_owner_user_id"), "book_listings", ["owner_user_id"], unique=False)

    op.create_table(
        "share_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("requester_user_id", sa.Integer(), nullable=False),
        sa.Column("status", request_status_enum, nullable=False),
        sa.Column("requested_days", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("selected_offered_book_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["book_listings.id"]),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["selected_offered_book_id"], ["book_listings.id"]),
    )
    op.create_index(op.f("ix_share_requests_book_id"), "share_requests", ["book_id"], unique=False)
    op.create_index(op.f("ix_share_requests_requester_user_id"), "share_requests", ["requester_user_id"], unique=False)

    op.create_table(
        "trade_request_offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("offered_book_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["offered_book_id"], ["book_listings.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["share_requests.id"]),
    )
    op.create_index(
        op.f("ix_trade_request_offers_offered_book_id"),
        "trade_request_offers",
        ["offered_book_id"],
        unique=False,
    )
    op.create_index(op.f("ix_trade_request_offers_request_id"), "trade_request_offers", ["request_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_trade_request_offers_request_id"), table_name="trade_request_offers")
    op.drop_index(op.f("ix_trade_request_offers_offered_book_id"), table_name="trade_request_offers")
    op.drop_table("trade_request_offers")

    op.drop_index(op.f("ix_share_requests_requester_user_id"), table_name="share_requests")
    op.drop_index(op.f("ix_share_requests_book_id"), table_name="share_requests")
    op.drop_table("share_requests")

    op.drop_index(op.f("ix_book_listings_owner_user_id"), table_name="book_listings")
    op.drop_table("book_listings")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
