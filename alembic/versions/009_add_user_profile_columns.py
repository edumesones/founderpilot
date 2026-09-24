"""Add user profile columns (OAuth, Gmail watch, Slack, subscription, status)

Revision ID: 0009_user_profile
Revises: 0008_usage
Create Date: 2026-09-23

The ``users`` table created in 0001_auth only covers the core profile fields.
``src/models/user.py`` additionally declares 14 columns (Google OAuth tokens,
Gmail watch state, Slack link, Stripe/subscription fields and account status)
that no migration created. This revision adds them so the model and the schema
agree.

Columns that are NOT NULL in the model carry a ``server_default`` so the
migration is safe on a table that already has rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009_user_profile"
down_revision: Union[str, None] = "0008_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Google OAuth tokens - encrypted (FEAT-003)
    op.add_column("users", sa.Column("google_access_token", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("google_refresh_token", sa.Text(), nullable=True))
    op.add_column(
        "users", sa.Column("google_token_expires_at", sa.DateTime(), nullable=True)
    )

    # Gmail watch (FEAT-003)
    op.add_column("users", sa.Column("gmail_history_id", sa.String(255), nullable=True))
    op.add_column(
        "users", sa.Column("gmail_watch_expires_at", sa.DateTime(), nullable=True)
    )

    # Slack connection (FEAT-006)
    op.add_column("users", sa.Column("slack_user_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("slack_team_id", sa.String(255), nullable=True))

    # Subscription (FEAT-002)
    op.add_column(
        "users", sa.Column("stripe_customer_id", sa.String(255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "subscription_plan",
            sa.String(50),
            nullable=False,
            server_default="trial",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "subscription_status",
            sa.String(50),
            nullable=False,
            server_default="trialing",
        ),
    )
    op.add_column("users", sa.Column("trial_ends_at", sa.DateTime(), nullable=True))

    # Status
    op.add_column(
        "users",
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_verified")
    op.drop_column("users", "is_active")
    op.drop_column("users", "trial_ends_at")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "subscription_plan")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "slack_team_id")
    op.drop_column("users", "slack_user_id")
    op.drop_column("users", "gmail_watch_expires_at")
    op.drop_column("users", "gmail_history_id")
    op.drop_column("users", "google_token_expires_at")
    op.drop_column("users", "google_refresh_token")
    op.drop_column("users", "google_access_token")
