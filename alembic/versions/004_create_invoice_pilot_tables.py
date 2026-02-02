"""Create InvoicePilot tables

Revision ID: 004
Revises: 003
Create Date: 2026-02-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create invoices table
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Gmail reference
        sa.Column(
            "gmail_message_id",
            sa.String(255),
            nullable=False,
            comment="Gmail message ID of the invoice email",
        ),
        # Invoice details
        sa.Column(
            "invoice_number",
            sa.String(255),
            nullable=True,
            comment="Invoice number extracted from PDF/email",
        ),
        sa.Column(
            "client_name",
            sa.String(255),
            nullable=False,
            comment="Client name or company",
        ),
        sa.Column(
            "client_email",
            sa.String(255),
            nullable=False,
            index=True,
            comment="Client email address for reminders",
        ),
        # Financial details
        sa.Column(
            "amount_total",
            sa.DECIMAL(15, 2),
            nullable=False,
            comment="Total invoice amount",
        ),
        sa.Column(
            "amount_paid",
            sa.DECIMAL(15, 2),
            server_default="0.00",
            nullable=False,
            comment="Amount paid (for partial payments)",
        ),
        sa.Column(
            "currency",
            sa.String(3),
            server_default="USD",
            nullable=False,
            comment="ISO 4217 currency code (USD, EUR, GBP, etc)",
        ),
        # Dates
        sa.Column(
            "issue_date",
            sa.Date,
            nullable=False,
            comment="Date invoice was issued",
        ),
        sa.Column(
            "due_date",
            sa.Date,
            nullable=False,
            index=True,
            comment="Payment due date",
        ),
        # Status tracking
        sa.Column(
            "status",
            sa.String(50),
            server_default="detected",
            nullable=False,
            index=True,
            comment="Status: detected, pending, overdue, partial, paid, rejected",
        ),
        # LLM extraction metadata
        sa.Column(
            "confidence",
            sa.DECIMAL(3, 2),
            server_default="0.00",
            nullable=False,
            comment="LLM extraction confidence (0.0-1.0)",
        ),
        # File storage
        sa.Column(
            "pdf_url",
            sa.String(512),
            nullable=True,
            comment="URL or path to stored invoice PDF",
        ),
        # Notes
        sa.Column(
            "notes",
            sa.Text,
            nullable=True,
            comment="User notes or comments",
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create unique constraint for tenant + gmail_message_id
    op.create_unique_constraint(
        "uq_invoice_tenant_gmail_message",
        "invoices",
        ["tenant_id", "gmail_message_id"],
    )

    # Create composite indexes for common queries
    op.create_index(
        "idx_invoice_tenant_status",
        "invoices",
        ["tenant_id", "status"],
    )
    op.create_index(
        "idx_invoice_tenant_due_date",
        "invoices",
        ["tenant_id", "due_date"],
    )
    op.create_index(
        "idx_invoice_status_due_date",
        "invoices",
        ["status", "due_date"],
    )

    # Create invoice_reminders table
    op.create_table(
        "invoice_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Scheduling
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
            comment="When reminder is scheduled to be sent",
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When reminder was actually sent",
        ),
        # Reminder type
        sa.Column(
            "type",
            sa.String(50),
            nullable=False,
            comment="Reminder type: pre_due, post_due_3d, post_due_7d, post_due_14d",
        ),
        # Status
        sa.Column(
            "status",
            sa.String(50),
            server_default="pending",
            nullable=False,
            index=True,
            comment="Status: pending, approved, sent, skipped, rejected",
        ),
        # Message content
        sa.Column(
            "draft_message",
            sa.Text,
            nullable=False,
            comment="LLM-generated reminder draft",
        ),
        sa.Column(
            "final_message",
            sa.Text,
            nullable=True,
            comment="Final message after human edit (if any)",
        ),
        # Approval tracking
        sa.Column(
            "approved_by",
            sa.String(255),
            nullable=True,
            comment="User ID who approved the reminder",
        ),
        # Response tracking
        sa.Column(
            "response_received",
            sa.Boolean,
            server_default="false",
            nullable=False,
            comment="Whether client responded to reminder",
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for reminders
    op.create_index(
        "idx_reminder_invoice_status",
        "invoice_reminders",
        ["invoice_id", "status"],
    )
    op.create_index(
        "idx_reminder_status_scheduled",
        "invoice_reminders",
        ["status", "scheduled_at"],
    )

    # Create invoice_actions table (audit trail)
    op.create_table(
        "invoice_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Optional workflow reference
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="LangGraph workflow run ID if applicable",
        ),
        # Action details
        sa.Column(
            "action_type",
            sa.String(100),
            nullable=False,
            index=True,
            comment="Action type: detected, confirmed, reminder_sent, marked_paid, etc",
        ),
        sa.Column(
            "actor",
            sa.String(255),
            nullable=False,
            comment="Who performed action: 'agent' or user_id",
        ),
        sa.Column(
            "details",
            postgresql.JSON,
            nullable=False,
            server_default="{}",
            comment="Action-specific data as JSON",
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
            comment="When action occurred",
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for actions
    op.create_index(
        "idx_action_invoice_timestamp",
        "invoice_actions",
        ["invoice_id", "timestamp"],
    )
    op.create_index(
        "idx_action_type_timestamp",
        "invoice_actions",
        ["action_type", "timestamp"],
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("invoice_actions")
    op.drop_table("invoice_reminders")
    op.drop_table("invoices")
