"""Create agent_audit_logs table

Revision ID: 007
Revises: 002
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_audit_logs table
    op.create_table(
        "agent_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("input_summary", sa.Text, nullable=True),
        sa.Column("output_summary", sa.Text, nullable=True),
        sa.Column("decision", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("escalated", sa.Boolean, nullable=False, default=False),
        sa.Column("authorized_by", sa.String(50), nullable=True),
        sa.Column("trace_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("rolled_back", sa.Boolean, nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range_check",
        ),
    )

    # Create indexes for performance
    op.create_index(
        "idx_agent_audit_logs_user_timestamp",
        "agent_audit_logs",
        ["user_id", sa.text("timestamp DESC")],
    )
    op.create_index(
        "idx_agent_audit_logs_agent_type",
        "agent_audit_logs",
        ["agent_type"],
    )
    op.create_index(
        "idx_agent_audit_logs_escalated",
        "agent_audit_logs",
        ["escalated"],
        postgresql_where=sa.text("escalated = true"),
    )

    # Create full-text search index
    # Note: This creates a GIN index on a tsvector generated from input_summary and output_summary
    op.execute(
        """
        CREATE INDEX idx_agent_audit_logs_search
        ON agent_audit_logs
        USING GIN(to_tsvector('english', COALESCE(input_summary, '') || ' ' || COALESCE(output_summary, '')))
        """
    )


def downgrade() -> None:
    op.drop_index("idx_agent_audit_logs_search", table_name="agent_audit_logs")
    op.drop_index("idx_agent_audit_logs_escalated", table_name="agent_audit_logs")
    op.drop_index("idx_agent_audit_logs_agent_type", table_name="agent_audit_logs")
    op.drop_index(
        "idx_agent_audit_logs_user_timestamp", table_name="agent_audit_logs"
    )
    op.drop_table("agent_audit_logs")
