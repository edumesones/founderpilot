"""Add usage_events and usage_counters tables for usage tracking

Revision ID: 008
Revises: 007
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create usage_events table
    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent", sa.String(20), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(255), unique=True, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create indexes for usage_events
    op.create_index(
        "idx_usage_events_tenant_agent",
        "usage_events",
        ["tenant_id", "agent", "created_at"],
    )
    op.create_index(
        "idx_usage_events_idempotency",
        "usage_events",
        ["idempotency_key"],
        unique=True,
    )

    # Create usage_counters table
    op.create_table(
        "usage_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent", sa.String(20), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=False), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=False), nullable=False),
        sa.Column("count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_event_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint("count >= 0", name="ck_usage_counter_count_non_negative"),
        sa.UniqueConstraint(
            "tenant_id",
            "agent",
            "period_start",
            name="uq_usage_counter_tenant_agent_period",
        ),
    )

    # Create indexes for usage_counters
    op.create_index(
        "idx_usage_counters_tenant_period",
        "usage_counters",
        ["tenant_id", "period_start"],
    )


def downgrade() -> None:
    # Drop usage_counters table and its indexes
    op.drop_index("idx_usage_counters_tenant_period", table_name="usage_counters")
    op.drop_table("usage_counters")

    # Drop usage_events table and its indexes
    op.drop_index("idx_usage_events_idempotency", table_name="usage_events")
    op.drop_index("idx_usage_events_tenant_agent", table_name="usage_events")
    op.drop_table("usage_events")
