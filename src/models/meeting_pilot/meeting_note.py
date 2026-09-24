"""MeetingNote model - User notes for meetings."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.meeting_pilot.meeting_record import MeetingRecord


class MeetingNote(Base, UUIDMixin):
    """Model for user notes attached to meetings.

    Notes can be pre-meeting (prep notes), post-meeting (summary),
    or action items identified after the meeting.
    """

    __tablename__ = "meeting_notes"

    # Foreign keys
    meeting_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("meeting_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Note content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Type: pre_meeting, post_meeting, action_item
    note_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    meeting: Mapped["MeetingRecord"] = relationship(
        "MeetingRecord", back_populates="notes"
    )

    def __repr__(self) -> str:
        return f"<MeetingNote {self.note_type} for meeting {self.meeting_id}>"

    @property
    def is_action_item(self) -> bool:
        """Check if this note is an action item."""
        return self.note_type == "action_item"
