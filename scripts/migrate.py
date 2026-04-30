from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import inspect

from app.core.config import get_settings
from app.db.session import engine

APP_TABLES = {"users", "book_listings", "share_requests", "trade_request_offers"}


def main() -> int:
    settings = get_settings()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    alembic_command = [sys.executable, "-m", "alembic"]

    if settings.database_url.startswith("sqlite") and "alembic_version" not in table_names and APP_TABLES.issubset(table_names):
        return subprocess.call([*alembic_command, "stamp", "head"])

    return subprocess.call([*alembic_command, "upgrade", "head"])


if __name__ == "__main__":
    raise SystemExit(main())
