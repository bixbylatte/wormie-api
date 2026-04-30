"""Clear existing Wormie application data for relaunch."""

from __future__ import annotations

from alembic import op

from app.db.reset import wipe_application_data


revision = "20260430_0002"
down_revision = "20260430_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    wipe_application_data(op.get_bind())


def downgrade() -> None:
    # Data removal is irreversible; downgrading only rewinds the migration marker.
    pass
