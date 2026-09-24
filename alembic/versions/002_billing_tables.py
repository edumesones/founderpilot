"""Create billing tables.

Revision ID: 0002_billing
Revises: 0001_auth
Create Date: 2026-01-31

Tables:
- plans: Product plans synced from Stripe
- subscriptions: Tenant subscriptions (one per tenant)
- stripe_invoices: Payment history from Stripe webhooks
- stripe_events: Webhook idempotency tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002_billing"
down_revision = "0001_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Plans table
    op.create_table(
        "plans",
        sa.Column("id", sa.String(50), primary_key=True),  # renamed in 0010
        sa.Column("stripe_product_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price_cents", sa.Integer, nullable=False),
        sa.Column("interval", sa.String(20), nullable=False, default="month"),
        sa.Column("agents_included", postgresql.JSONB, nullable=False),
        sa.Column("limits", postgresql.JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("stripe_subscription_id", sa.String(50), nullable=True),
        sa.Column("stripe_customer_id", sa.String(50), nullable=False),
        sa.Column(
            "plan_id", sa.String(50), sa.ForeignKey("plans.id"), nullable=True
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime, nullable=True),
        sa.Column("current_period_start", sa.DateTime, nullable=True),
        sa.Column("current_period_end", sa.DateTime, nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean, default=False),
        sa.Column("canceled_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Stripe invoices table (distinct from the InvoicePilot "invoices" table
    # created in 0005_invoice_pilot)
    op.create_table(
        "stripe_invoices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subscriptions.id"),
            nullable=True,
        ),
        sa.Column("stripe_invoice_id", sa.String(50), unique=True, nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), default="usd"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("period_start", sa.DateTime, nullable=True),
        sa.Column("period_end", sa.DateTime, nullable=True),
        sa.Column("paid_at", sa.DateTime, nullable=True),
        sa.Column("hosted_invoice_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Stripe events table (for webhook idempotency)
    op.create_table(
        "stripe_events",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("processed_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Indexes
    op.create_index("idx_subscriptions_tenant", "subscriptions", ["tenant_id"])
    op.create_index("idx_subscriptions_status", "subscriptions", ["status"])
    op.create_index("idx_subscriptions_stripe_id", "subscriptions", ["stripe_subscription_id"])
    op.create_index("idx_stripe_invoices_tenant", "stripe_invoices", ["tenant_id"])
    op.create_index("idx_stripe_invoices_status", "stripe_invoices", ["status"])


def downgrade() -> None:
    op.drop_index("idx_stripe_invoices_status", table_name="stripe_invoices")
    op.drop_index("idx_stripe_invoices_tenant", table_name="stripe_invoices")
    op.drop_index("idx_subscriptions_stripe_id", table_name="subscriptions")
    op.drop_index("idx_subscriptions_status", table_name="subscriptions")
    op.drop_index("idx_subscriptions_tenant", table_name="subscriptions")
    op.drop_table("stripe_events")
    op.drop_table("stripe_invoices")
    op.drop_table("subscriptions")
    op.drop_table("plans")
