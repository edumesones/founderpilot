"""MeetingRecord model - Synced calendar events."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class MeetingRecord(Base, UUIDMixin, TimestampMixin):
    """Model for synced calendar meeting records.

    Stores meeting metadata from Google Calendar along with
    generated briefs and processing status.
    """

    __tablename__ = "meeting_records"
    __table_args__ = (
        UniqueConstraint("user_id", "calendar_event_id", name="uq_meeting_user_event"),
    )

    # Foreign keys
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Calendar identifiers
    calendar_event_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Meeting details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Attendees as JSON array: [{email, name, response_status}]
    attendees: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default="[]", nullable=False
    )

    # Flags
    is_external: Mapped[bool] = mapped_column(default=False)

    # Brief
    brief_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    brief_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brief_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status: pending, brief_sent, completed, cancelled, skipped
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Audit
    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    trace_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    notes: Mapped[list["MeetingNote"]] = relationship(
        "MeetingNote", back_populates="meeting", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MeetingRecord {self.title} @ {self.start_time}>"

    @property
    def external_attendees(self) -> list[dict[str, Any]]:
        """Get list of external (non-organizer) attendees."""
        return [
            a
            for a in self.attendees
            if a.get("email") and not a.get("organizer", False)
        ]

    @property
    def attendee_emails(self) -> list[str]:
        """Get list of attendee email addresses."""
        return [a.get("email") for a in self.attendees if a.get("email")]

    @property
    def duration_minutes(self) -> int:
        """Calculate meeting duration in minutes."""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)


# Import for relationship typing
from src.models.meeting_pilot.meeting_note import MeetingNote  # noqa: E402
