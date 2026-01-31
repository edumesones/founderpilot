"""Slack installation model for storing OAuth tokens and workspace info."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.core.database import Base


class SlackInstallation(Base):
    """
    Stores Slack OAuth installation data for each user.

    Each user can have one Slack workspace connected (MVP).
    Tokens are stored encrypted using Fernet (AES).
    """
    __tablename__ = "slack_installations"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to users table
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One installation per user (MVP)
    )

    # Slack workspace identifiers
    team_id = Column(String(32), nullable=False)
    team_name = Column(String(255), nullable=True)
    enterprise_id = Column(String(32), nullable=True)  # For Enterprise Grid (future)

    # Bot credentials
    bot_user_id = Column(String(32), nullable=False)
    bot_access_token = Column(Text, nullable=False)  # Encrypted

    # User credentials (optional, for user-level actions)
    user_access_token = Column(Text, nullable=True)  # Encrypted
    user_slack_id = Column(String(32), nullable=True)

    # DM channel ID for sending notifications
    dm_channel_id = Column(String(32), nullable=True)

    # OAuth scopes granted
    scopes = Column(Text, nullable=True)  # Comma-separated

    # Timestamps
    installed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship to User model
    # Note: User model must define back_populates="slack_installation"
    user = relationship("User", back_populates="slack_installation")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_slack_installations_user_id", "user_id"),
        Index("ix_slack_installations_team_id", "team_id"),
        Index("ix_slack_installations_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<SlackInstallation(id={self.id}, team={self.team_name}, user_id={self.user_id})>"

    @property
    def is_connected(self) -> bool:
        """Check if the installation is active and has valid tokens."""
        return self.is_active and self.bot_access_token is not None
