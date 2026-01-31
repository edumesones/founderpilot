"""
User model for authentication.
"""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.integration import Integration
    from src.models.refresh_token import RefreshToken


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model representing a FounderPilot user.

    Attributes:
        id: Unique identifier (UUID)
        email: User's email address (unique, from Google)
        name: User's display name
        picture_url: URL to user's profile picture
        google_id: Google's unique user ID (unique)
        onboarding_completed: Whether user completed onboarding
        created_at: When the user was created
        updated_at: When the user was last updated
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    picture_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    google_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
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
