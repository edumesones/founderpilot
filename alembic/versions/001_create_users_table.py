"""Create users table

Revision ID: 001
Revises:
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("picture_url", sa.String(500), nullable=True),
        # Google OAuth
        sa.Column("google_access_token", sa.Text, nullable=True),
        sa.Column("google_refresh_token", sa.Text, nullable=True),
        sa.Column("google_token_expires_at", sa.DateTime, nullable=True),
        # Gmail watch
        sa.Column("gmail_history_id", sa.String(255), nullable=True),
        sa.Column("gmail_watch_expires_at", sa.DateTime, nullable=True),
        # Slack
        sa.Column("slack_user_id", sa.String(255), nullable=True),
        sa.Column("slack_team_id", sa.String(255), nullable=True),
        # Subscription
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("subscription_plan", sa.String(50), default="trial"),
        sa.Column("subscription_status", sa.String(50), default="trialing"),
        sa.Column("trial_ends_at", sa.DateTime, nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_verified", sa.Boolean, default=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("users")
