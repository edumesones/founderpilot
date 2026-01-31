"""
Integration model for OAuth connections (Gmail, Slack, etc).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.user import User


class Integration(Base, UUIDMixin, TimestampMixin):
    """
    Integration model for storing OAuth tokens for external services.

    Attributes:
        id: Unique identifier (UUID)
        user_id: FK to the user who owns this integration
        provider: Integration provider name (gmail, slack)
        access_token_encrypted: Encrypted access token
        refresh_token_encrypted: Encrypted refresh token (optional)
        token_expires_at: When the access token expires
        scopes: List of granted OAuth scopes
        metadata: Provider-specific metadata (workspace_id, etc)
        status: Integration status (active, expired, revoked)
        connected_at: When the integration was first connected
        created_at: When the record was created
        updated_at: When the record was last updated
    """

    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    access_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scopes: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=True,
        default=list,
    )
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="integrations",
    )

    def __repr__(self) -> str:
        return f"<Integration(id={self.id}, provider={self.provider}, user_id={self.user_id})>"

    @property
    def is_active(self) -> bool:
        """Check if integration is active."""
        return self.status == "active"

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.token_expires_at is None:
            return False
        return datetime.now(self.token_expires_at.tzinfo) > self.token_expires_at
