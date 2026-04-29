from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.book import BookListing
from app.models.enums import ListingStatus, RequestStatus, ShareMode
from app.models.share_request import ShareRequest, TradeRequestOffer
from app.models.user import User

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01\xe5'\xd4\xa2\x00\x00\x00\x00IEND\xaeB`\x82"
)


def write_cover(name: str) -> str:
    storage_dir = get_settings().cover_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{name}.png"
    (storage_dir / file_name).write_bytes(PNG_BYTES)
    return file_name


def seed() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    storage_dir = get_settings().cover_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    for file_path in storage_dir.iterdir():
        if file_path.is_file():
            file_path.unlink()

    session = SessionLocal()
    try:
        users = {
            "alice": User(display_name="Alice", email="alice@wormie.app", password_hash=hash_password("wormie1234")),
            "ben": User(display_name="Ben", email="ben@wormie.app", password_hash=hash_password("wormie1234")),
            "cami": User(display_name="Cami", email="cami@wormie.app", password_hash=hash_password("wormie1234")),
        }
        session.add_all(users.values())
        session.flush()

        books = {
            "alice_lend": BookListing(
                owner_user_id=users["alice"].id,
                share_mode=ShareMode.LEND,
                status=ListingStatus.AVAILABLE,
                max_lend_days=14,
                title="The Pragmatic Programmer",
                author="Andrew Hunt & David Thomas",
                genre="Software Engineering",
                details_url="https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/",
                cover_object_key=write_cover("alice_lend"),
            ),
            "alice_trade": BookListing(
                owner_user_id=users["alice"].id,
                share_mode=ShareMode.TRADE,
                status=ListingStatus.AVAILABLE,
                max_lend_days=None,
                title="Atomic Habits",
                author="James Clear",
                genre="Self Improvement",
                details_url="https://jamesclear.com/atomic-habits",
                cover_object_key=write_cover("alice_trade"),
            ),
            "ben_trade": BookListing(
                owner_user_id=users["ben"].id,
                share_mode=ShareMode.TRADE,
                status=ListingStatus.AVAILABLE,
                max_lend_days=None,
                title="Clean Code",
                author="Robert C. Martin",
                genre="Software Engineering",
                details_url="https://www.pearson.com/en-us/subject-catalog/p/clean-code/P200000009529/9780136083238",
                cover_object_key=write_cover("ben_trade"),
            ),
            "ben_trade_2": BookListing(
                owner_user_id=users["ben"].id,
                share_mode=ShareMode.TRADE,
                status=ListingStatus.AVAILABLE,
                max_lend_days=None,
                title="The Phoenix Project",
                author="Gene Kim, Kevin Behr, George Spafford",
                genre="Technology",
                details_url="https://itrevolution.com/product/the-phoenix-project/",
                cover_object_key=write_cover("ben_trade_2"),
            ),
            "cami_lend": BookListing(
                owner_user_id=users["cami"].id,
                share_mode=ShareMode.LEND,
                status=ListingStatus.AVAILABLE,
                max_lend_days=10,
                title="Deep Work",
                author="Cal Newport",
                genre="Productivity",
                details_url="https://www.calnewport.com/books/deep-work/",
                cover_object_key=write_cover("cami_lend"),
            ),
        }
        session.add_all(books.values())
        session.flush()

        pending_lend = ShareRequest(
            book_id=books["alice_lend"].id,
            requester_user_id=users["ben"].id,
            status=RequestStatus.PENDING,
            requested_days=7,
            created_at=datetime.now(UTC),
        )
        pending_trade = ShareRequest(
            book_id=books["ben_trade"].id,
            requester_user_id=users["alice"].id,
            status=RequestStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        session.add_all([pending_lend, pending_trade])
        session.flush()
        session.add(TradeRequestOffer(request_id=pending_trade.id, offered_book_id=books["alice_trade"].id))

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed()
    print("Seeded demo users and book listings.")
