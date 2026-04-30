from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

APP_DATA_TABLES = ("trade_request_offers", "share_requests", "book_listings", "users")


def wipe_application_data(connection: Connection) -> None:
    dialect_name = connection.dialect.name

    if dialect_name == "postgresql":
        table_names = ", ".join(APP_DATA_TABLES)
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
        return

    for table_name in APP_DATA_TABLES:
        connection.execute(text(f"DELETE FROM {table_name}"))

    if dialect_name == "sqlite":
        _reset_sqlite_sequences(connection)


def _reset_sqlite_sequences(connection: Connection) -> None:
    has_sequence_table = connection.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'")
    ).scalar_one_or_none()
    if not has_sequence_table:
        return

    placeholders = ", ".join(f":table_{index}" for index in range(len(APP_DATA_TABLES)))
    params = {f"table_{index}": table_name for index, table_name in enumerate(APP_DATA_TABLES)}
    connection.execute(text(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})"), params)
