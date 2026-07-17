"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("phone_number", sa.String, unique=True, index=True, nullable=False),
        sa.Column("email", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "otp_challenges",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("phone_number", sa.String, index=True, nullable=False),
        sa.Column("code_hash", sa.String, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("consumed", sa.Boolean, default=False, nullable=False),
        sa.Column("attempt_count", sa.Integer, default=0, nullable=False),
    )
    op.create_table(
        "retailers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String, unique=True, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("keyword", sa.String, nullable=False),
        sa.Column("canonical_image_url", sa.String, nullable=True),
    )
    op.create_table(
        "watch_targets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("retailer_slug", sa.String, nullable=False),
        sa.Column("city", sa.String, nullable=False),
        sa.Column("pincode", sa.String, nullable=False),
        sa.Column("keyword", sa.String, nullable=False),
        sa.Column("interval_seconds", sa.Integer, default=300, nullable=False),
        sa.Column("last_checked_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint(
            "retailer_slug", "city", "pincode", "keyword", name="uq_watch_target"
        ),
    )
    op.create_table(
        "watches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "product_id", sa.Integer, sa.ForeignKey("products.id"), nullable=False
        ),
        sa.Column(
            "watch_target_id",
            sa.Integer,
            sa.ForeignKey("watch_targets.id"),
            nullable=False,
        ),
        sa.Column("interval_seconds", sa.Integer, default=300, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
    )
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "watch_target_id",
            sa.Integer,
            sa.ForeignKey("watch_targets.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("availability", sa.String, nullable=False),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("mrp", sa.Float, nullable=True),
        sa.Column("discount_pct", sa.Float, nullable=True),
        sa.Column("eta_minutes", sa.Integer, nullable=True),
        sa.Column("store_name", sa.String, nullable=True),
        sa.Column("image_url", sa.String, nullable=True),
        sa.Column("quantity_label", sa.String, nullable=True),
        sa.Column("variants", sa.JSON, nullable=False, default=list),
        sa.Column("product_url", sa.String, nullable=True),
    )
    op.create_table(
        "detection_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "watch_target_id",
            sa.Integer,
            sa.ForeignKey("watch_targets.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "snapshot_id", sa.Integer, sa.ForeignKey("snapshots.id"), nullable=False
        ),
        sa.Column(
            "previous_snapshot_id",
            sa.Integer,
            sa.ForeignKey("snapshots.id"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("config_json", sa.JSON, nullable=False, default=dict),
        sa.Column("is_verified", sa.Boolean, default=False, nullable=False),
    )
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "detection_event_id",
            sa.Integer,
            sa.ForeignKey("detection_events.id"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            sa.Integer,
            sa.ForeignKey("notification_channels.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("sent_at", sa.DateTime, nullable=False),
        sa.Column("dedup_key", sa.String, nullable=False, index=True),
    )
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("key", sa.String, nullable=False),
        sa.Column("value_json", sa.JSON, nullable=False, default=dict),
    )


def downgrade() -> None:
    for table in [
        "settings",
        "notification_logs",
        "notification_channels",
        "detection_events",
        "snapshots",
        "watches",
        "watch_targets",
        "products",
        "retailers",
        "otp_challenges",
        "users",
    ]:
        op.drop_table(table)
