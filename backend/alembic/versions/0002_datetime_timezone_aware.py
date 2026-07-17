"""make datetime columns timezone-aware

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

COLUMNS = [
    ("users", "created_at"),
    ("otp_challenges", "expires_at"),
    ("otp_challenges", "created_at"),
    ("watch_targets", "last_checked_at"),
    ("snapshots", "timestamp"),
    ("detection_events", "created_at"),
    ("notification_logs", "sent_at"),
    ("system_logs", "created_at"),
]


def upgrade() -> None:
    for table, column in COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, column in COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=False),
        )
