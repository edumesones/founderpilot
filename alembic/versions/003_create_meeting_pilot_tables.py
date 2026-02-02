"""Create MeetingPilot tables

Revision ID: 003
Revises: 002
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create meeting_records table
    op.create_table(
        "meeting_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Calendar identifiers
        sa.Column("calendar_event_id", sa.String(255), nullable=False),
        # Meeting details
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(500), nullable=True),
        # Attendees stored as JSON array: [{email, name, response_status}]
        sa.Column("attendees", postgresql.JSONB, server_default="[]"),
        # Flags
        sa.Column("is_external", sa.Boolean, default=False),
        # Brief
        sa.Column("brief_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("brief_content", sa.Text, nullable=True),
        sa.Column("brief_confidence", sa.Float, nullable=True),
        # Status: pending, brief_sent, completed, cancelled, skipped
        sa.Column("status", sa.String(50), default="pending", nullable=False),
        # Snooze tracking
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        # Audit
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trace_id", sa.String(255), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        # Unique constraint: one record per user per calendar event
        sa.UniqueConstraint("user_id", "calendar_event_id", name="uq_meeting_user_event"),
    )

    # Create indexes for common queries
    op.create_index(
        "idx_meeting_records_user_start",
        "meeting_records",
        ["user_id", "start_time"],
    )
    op.create_index(
        "idx_meeting_records_status_pending",
        "meeting_records",
        ["status"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # Create meeting_notes table
    op.create_table(
        "meeting_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meeting_records.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Note content
        sa.Column("content", sa.Text, nullable=False),
        # Type: pre_meeting, post_meeting, action_item
        sa.Column("note_type", sa.String(50), nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create meeting_pilot_configs table
    op.create_table(
        "meeting_pilot_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
        # Status
        sa.Column("is_enabled", sa.Boolean, default=True),
        # Timing
        sa.Column("brief_minutes_before", sa.Integer, default=30),
        # Filters
        sa.Column("only_external_meetings", sa.Boolean, default=True),
        sa.Column("min_attendees", sa.Integer, default=1),
        # Thresholds
        sa.Column("escalation_threshold", sa.Numeric(3, 2), default=0.80),
        # Stats
        sa.Column("total_meetings_processed", sa.Integer, default=0),
        sa.Column("total_briefs_sent", sa.Integer, default=0),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("meeting_pilot_configs")
    op.drop_table("meeting_notes")
    op.drop_index("idx_meeting_records_status_pending", table_name="meeting_records")
    op.drop_index("idx_meeting_records_user_start", table_name="meeting_records")
    op.drop_table("meeting_records")
