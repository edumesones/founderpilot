"""MeetingPilotConfig model - Per-user agent configuration."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDMixin


class MeetingPilotConfig(Base, UUIDMixin, TimestampMixin):
    """Model for per-user MeetingPilot configuration.

    Stores user preferences for how the MeetingPilot agent
    should behave, including timing, filtering, and thresholds.
    """

    __tablename__ = "meeting_pilot_configs"

    # Foreign key - unique per user
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timing - how many minutes before meeting to send brief
    brief_minutes_before: Mapped[int] = mapped_column(Integer, default=30)

    # Filters
    only_external_meetings: Mapped[bool] = mapped_column(Boolean, default=True)
    min_attendees: Mapped[int] = mapped_column(Integer, default=1)

    # Thresholds
    escalation_threshold: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.80")
    )

    # Stats
    total_meetings_processed: Mapped[int] = mapped_column(Integer, default=0)
    total_briefs_sent: Mapped[int] = mapped_column(Integer, default=0)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<MeetingPilotConfig user={self.user_id} enabled={self.is_enabled}>"

    def should_process_meeting(
        self, is_external: bool, attendee_count: int
    ) -> bool:
        """Check if a meeting should be processed based on config.

        Args:
            is_external: Whether meeting has external attendees
            attendee_count: Number of attendees

        Returns:
            True if meeting should be processed
        """
        if not self.is_enabled:
            return False

        if self.only_external_meetings and not is_external:
            return False

        if attendee_count < self.min_attendees:
            return False

        return True

    def increment_processed(self) -> None:
        """Increment the processed meetings counter."""
        self.total_meetings_processed += 1

    def increment_briefs_sent(self) -> None:
        """Increment the briefs sent counter."""
        self.total_briefs_sent += 1
