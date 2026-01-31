"""User model for authentication and tenant isolation."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.integration import Integration
    from src.models.refresh_token import RefreshToken


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model representing a FounderPilot user.

    Combines authentication (FEAT-001) with subscription and integration fields.
    """

    __tablename__ = "users"

    # Profile (FEAT-001)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    picture_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    google_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    # Onboarding (FEAT-001)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Google OAuth tokens - encrypted (FEAT-003)
    google_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Gmail watch (FEAT-003)
    gmail_history_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gmail_watch_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Slack connection (FEAT-006)
    slack_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    slack_team_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Subscription (FEAT-002)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(50), default="trial")
    subscription_status: Mapped[str] = mapped_column(String(50), default="trialing")
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships (FEAT-001)
    integrations: Mapped[List["Integration"]] = relationship(
        "Integration",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
