"""Add slack_installations table

Revision ID: 001
Revises:
Create Date: 2026-01-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create slack_installations table."""
    op.create_table(
        'slack_installations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('team_id', sa.String(32), nullable=False),
        sa.Column('team_name', sa.String(255), nullable=True),
        sa.Column('enterprise_id', sa.String(32), nullable=True),
        sa.Column('bot_user_id', sa.String(32), nullable=False),
        sa.Column('bot_access_token', sa.Text(), nullable=False),
        sa.Column('user_access_token', sa.Text(), nullable=True),
        sa.Column('user_slack_id', sa.String(32), nullable=True),
        sa.Column('dm_channel_id', sa.String(32), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('installed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id'),
    )

    # Create indexes for common queries
    op.create_index('ix_slack_installations_user_id', 'slack_installations', ['user_id'])
    op.create_index('ix_slack_installations_team_id', 'slack_installations', ['team_id'])
    op.create_index('ix_slack_installations_is_active', 'slack_installations', ['is_active'])


def downgrade() -> None:
    """Drop slack_installations table."""
    op.drop_index('ix_slack_installations_is_active', table_name='slack_installations')
    op.drop_index('ix_slack_installations_team_id', table_name='slack_installations')
    op.drop_index('ix_slack_installations_user_id', table_name='slack_installations')
    op.drop_table('slack_installations')
