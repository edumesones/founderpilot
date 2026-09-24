"""Meeting-related Pydantic schemas."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AttendeeData(BaseModel):
    """Schema for meeting attendee data."""

    email: str
    name: Optional[str] = None
    response_status: Literal["needsAction", "accepted", "declined", "tentative"] = (
        "needsAction"
    )
    is_organizer: bool = False
    is_self: bool = False


class MeetingRecordCreate(BaseModel):
    """Schema for creating a meeting record from calendar sync."""

    calendar_event_id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: list[AttendeeData] = Field(default_factory=list)
    is_external: bool = False


class MeetingRecordResponse(BaseModel):
    """Schema for meeting record API response."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    calendar_event_id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    attendees: list[AttendeeData]
    is_external: bool
    brief_sent_at: Optional[datetime]
    brief_content: Optional[str]
    brief_confidence: Optional[float]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    # Computed fields
    duration_minutes: int
    has_brief: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_computed(cls, meeting) -> "MeetingRecordResponse":
        """Create response with computed fields from ORM object."""
        return cls(
            id=meeting.id,
            tenant_id=meeting.tenant_id,
            user_id=meeting.user_id,
            calendar_event_id=meeting.calendar_event_id,
            title=meeting.title,
            description=meeting.description,
            start_time=meeting.start_time,
            end_time=meeting.end_time,
            location=meeting.location,
            attendees=[AttendeeData(**a) for a in meeting.attendees],
            is_external=meeting.is_external,
            brief_sent_at=meeting.brief_sent_at,
            brief_content=meeting.brief_content,
            brief_confidence=meeting.brief_confidence,
            status=meeting.status,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
            duration_minutes=meeting.duration_minutes,
            has_brief=meeting.brief_content is not None,
        )


class MeetingListResponse(BaseModel):
    """Schema for paginated meeting list response."""

    meetings: list[MeetingRecordResponse]
    total: int
    page: int = 1
    page_size: int = 20


class MeetingNoteCreate(BaseModel):
    """Schema for creating a meeting note."""

    content: str = Field(..., min_length=1, max_length=10000)
    note_type: Literal["pre_meeting", "post_meeting", "action_item"] = "post_meeting"


class MeetingNoteResponse(BaseModel):
    """Schema for meeting note API response."""

    id: UUID
    meeting_id: UUID
    user_id: UUID
    content: str
    note_type: str
    created_at: datetime

    class Config:
        from_attributes = True
