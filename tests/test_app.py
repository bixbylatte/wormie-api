from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.base import Base
from app.db.reset import APP_DATA_TABLES, wipe_application_data
from app.db.session import engine
from app.main import app

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01\xe5'\xd4\xa2\x00\x00\x00\x00IEND\xaeB`\x82"
)


def reset_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    storage_dir = get_settings().cover_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    for file_path in storage_dir.iterdir():
        if file_path.is_file():
            file_path.unlink()


def register(client: TestClient, display_name: str, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"display_name": display_name, "email": email, "password": "verysecurepassword"},
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_book(
    client: TestClient,
    token: str,
    *,
    share_mode: str,
    title: str,
    author: str,
    max_lend_days: int | None = None,
) -> dict:
    data = {
        "share_mode": share_mode,
        "title": title,
        "author": author,
        "genre": "Technology",
        "details_url": "https://example.com/book",
    }
    if max_lend_days is not None:
        data["max_lend_days"] = str(max_lend_days)

    response = client.post(
        "/api/v1/books",
        data=data,
        files={"cover": ("cover.png", PNG_BYTES, "image/png")},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def test_lend_flow() -> None:
    reset_state()
    with TestClient(app) as client:
        owner = register(client, "Owner", "owner@example.com")
        borrower = register(client, "Borrower", "borrower@example.com")

        listing = create_book(
            client,
            owner["token"],
            share_mode="LEND",
            title="Designing Data-Intensive Applications",
            author="Martin Kleppmann",
            max_lend_days=14,
        )

        request_response = client.post(
            f"/api/v1/requests/books/{listing['id']}",
            json={"requested_days": 10},
            headers=auth_headers(borrower["token"]),
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["id"]

        approve_response = client.post(
            f"/api/v1/requests/{request_id}/approve",
            json={"selected_offered_book_id": None},
            headers=auth_headers(owner["token"]),
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "APPROVED"
        assert approve_response.json()["due_date"] is not None

        return_response = client.post(
            f"/api/v1/requests/{request_id}/return",
            headers=auth_headers(owner["token"]),
        )
        assert return_response.status_code == 200
        assert return_response.json()["status"] == "RETURNED"

        books_response = client.get("/api/v1/books", headers=auth_headers(owner["token"]))
        assert books_response.status_code == 200
        assert books_response.json()["items"][0]["status"] == "AVAILABLE"


def test_trade_flow() -> None:
    reset_state()
    with TestClient(app) as client:
        owner = register(client, "Owner", "owner@example.com")
        requester = register(client, "Requester", "requester@example.com")
        outsider = register(client, "Outsider", "outsider@example.com")

        owner_book = create_book(
            client,
            owner["token"],
            share_mode="TRADE",
            title="Refactoring",
            author="Martin Fowler",
        )
        offered_book_one = create_book(
            client,
            requester["token"],
            share_mode="TRADE",
            title="Clean Architecture",
            author="Robert C. Martin",
        )
        offered_book_two = create_book(
            client,
            requester["token"],
            share_mode="TRADE",
            title="Domain-Driven Design",
            author="Eric Evans",
        )
        outsider_offer = create_book(
            client,
            outsider["token"],
            share_mode="TRADE",
            title="Thinking in Systems",
            author="Donella Meadows",
        )

        request_response = client.post(
            f"/api/v1/requests/books/{owner_book['id']}",
            json={"offered_book_ids": [offered_book_one["id"], offered_book_two["id"]]},
            headers=auth_headers(requester["token"]),
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["id"]

        competing_request = client.post(
            f"/api/v1/requests/books/{offered_book_two['id']}",
            json={"offered_book_ids": [outsider_offer["id"]]},
            headers=auth_headers(outsider["token"]),
        )
        assert competing_request.status_code == 201
        competing_request_id = competing_request.json()["id"]

        approve_response = client.post(
            f"/api/v1/requests/{request_id}/approve",
            json={"selected_offered_book_id": offered_book_two["id"]},
            headers=auth_headers(owner["token"]),
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["selected_offered_book_id"] == offered_book_two["id"]

        competing_requests = client.get("/api/v1/requests", headers=auth_headers(outsider["token"]))
        assert competing_requests.status_code == 200
        rejected_competing = next(item for item in competing_requests.json()["your_requests"] if item["id"] == competing_request_id)
        assert rejected_competing["status"] == "REJECTED"

        availability_response = client.patch(
            f"/api/v1/books/{offered_book_two['id']}/availability",
            json={"status": "AVAILABLE"},
            headers=auth_headers(requester["token"]),
        )
        assert availability_response.status_code == 409

        complete_response = client.post(
            f"/api/v1/requests/{request_id}/complete",
            headers=auth_headers(owner["token"]),
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "COMPLETED"

        books_response = client.get(
            "/api/v1/books?include_unavailable=true",
            headers=auth_headers(owner["token"]),
        )
        assert books_response.status_code == 200
        archived_ids = {item["id"] for item in books_response.json()["items"] if item["status"] == "ARCHIVED"}
        assert owner_book["id"] in archived_ids
        assert offered_book_two["id"] in archived_ids


def test_wipe_application_data_clears_users_and_related_records() -> None:
    reset_state()
    with TestClient(app) as client:
        owner = register(client, "Owner", "owner@example.com")
        borrower = register(client, "Borrower", "borrower@example.com")

        listing = create_book(
            client,
            owner["token"],
            share_mode="LEND",
            title="Working in Public",
            author="Nadia Eghbal",
            max_lend_days=7,
        )

        request_response = client.post(
            f"/api/v1/requests/books/{listing['id']}",
            json={"requested_days": 5},
            headers=auth_headers(borrower["token"]),
        )
        assert request_response.status_code == 201

    with engine.begin() as connection:
        wipe_application_data(connection)

    with engine.connect() as connection:
        for table_name in APP_DATA_TABLES:
            row_count = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
            assert row_count == 0

    with TestClient(app) as client:
        reused_email = client.post(
            "/api/v1/auth/register",
            json={"display_name": "Fresh Owner", "email": "owner@example.com", "password": "verysecurepassword"},
        )
        assert reused_email.status_code == 201
