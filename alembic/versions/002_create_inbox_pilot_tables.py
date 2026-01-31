"""Create InboxPilot tables

Revision ID: 002
Revises: 001
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create email_records table
    op.create_table(
        "email_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Gmail identifiers
        sa.Column("gmail_message_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("thread_id", sa.String(255), nullable=False, index=True),
        # Email metadata
        sa.Column("sender", sa.String(255), nullable=False),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("snippet", sa.String(500), nullable=True),
        sa.Column("received_at", sa.DateTime, nullable=False),
        # Classification
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("classification_reasoning", sa.Text, nullable=True),
        # Status
        sa.Column("status", sa.String(50), default="pending", nullable=False, index=True),
        # Draft
        sa.Column("draft_content", sa.Text, nullable=True),
        sa.Column("draft_confidence", sa.Float, nullable=True),
        sa.Column("draft_tone", sa.String(50), nullable=True),
        # Action
        sa.Column("action_taken", sa.String(50), nullable=True),
        # Timestamps
        sa.Column("processed_at", sa.DateTime, nullable=True),
        sa.Column("escalated_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        # Audit
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trace_id", sa.String(255), nullable=True),
        # Human review
        sa.Column("human_decision", sa.String(50), nullable=True),
        sa.Column("human_edited_content", sa.Text, nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create composite indexes for common queries
    op.create_index(
        "idx_email_records_user_status",
        "email_records",
        ["user_id", "status"],
    )
    op.create_index(
        "idx_email_records_user_received",
        "email_records",
        ["user_id", "received_at"],
    )

    # Create inbox_pilot_configs table
    op.create_table(
        "inbox_pilot_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
        # Thresholds
        sa.Column("escalation_threshold", sa.Float, default=0.8),
        sa.Column("draft_threshold", sa.Float, default=0.7),
        # Behavior
        sa.Column("auto_archive_spam", sa.Boolean, default=True),
        sa.Column("draft_for_routine", sa.Boolean, default=True),
        sa.Column("escalate_urgent", sa.Boolean, default=True),
        sa.Column("auto_send_high_confidence", sa.Boolean, default=False),
        # VIP contacts
        sa.Column("vip_domains", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("vip_emails", postgresql.ARRAY(sa.String), server_default="{}"),
        # Ignored
        sa.Column("ignore_senders", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("ignore_domains", postgresql.ARRAY(sa.String), server_default="{}"),
        # Labels
        sa.Column("watch_labels", postgresql.ARRAY(sa.String), server_default="{}"),
        # Signature
        sa.Column("email_signature", sa.String(1000), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("paused_until", sa.DateTime, nullable=True),
        sa.Column("pause_reason", sa.String(255), nullable=True),
        # Stats
        sa.Column("total_emails_processed", sa.Integer, default=0),
        sa.Column("total_drafts_sent", sa.Integer, default=0),
        sa.Column("total_escalations", sa.Integer, default=0),
        # Timestamps
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("inbox_pilot_configs")
    op.drop_index("idx_email_records_user_received")
    op.drop_index("idx_email_records_user_status")
    op.drop_table("email_records")
