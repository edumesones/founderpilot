"""Rename plans.id to plans.stripe_price_id

Revision ID: 0010_plan_price_id
Revises: 0009_user_profile
Create Date: 2026-09-23

A Plan *is* a Stripe Price. `subscriptions.plan_id` is filled straight from
`stripe_subscription["items"]["data"][0]["price"]["id"]`, so the primary key of
`plans` is the Stripe price id -- 0002 already said as much in a comment
(`# stripe_price_id`) while naming the column `id`. This gives the column the
name the domain uses.

Postgres carries the primary key constraint and the incoming foreign key from
`subscriptions.plan_id` across a column rename, so no constraint has to be
rebuilt.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_plan_price_id"
down_revision: Union[str, None] = "0009_user_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("plans", "id", new_column_name="stripe_price_id")


def downgrade() -> None:
    op.alter_column("plans", "stripe_price_id", new_column_name="id")
