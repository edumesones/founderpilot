"""Brief-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ParticipantContext(BaseModel):
    """Context gathered for a single meeting participant."""

    email: str
    name: Optional[str] = None
    email_count: int = 0
    recent_subjects: list[str] = Field(default_factory=list)
    last_contact: Optional[datetime] = None
    is_first_contact: bool = True
    summary: Optional[str] = None


class BriefGenerationRequest(BaseModel):
    """Request schema for generating a meeting brief."""

    meeting_id: UUID
    include_email_context: bool = True
    max_emails_per_participant: int = 5


class BriefResult(BaseModel):
    """Result of brief generation."""

    meeting_id: UUID
    content: str
    confidence: float = Field(..., ge=0, le=1)
    participant_contexts: list[ParticipantContext] = Field(default_factory=list)
    suggested_objectives: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime

    @property
    def is_high_confidence(self) -> bool:
        """Check if brief has high confidence (>= 0.8)."""
        return self.confidence >= 0.8

    @property
    def has_context(self) -> bool:
        """Check if brief has any participant context."""
        return len(self.participant_contexts) > 0 and any(
            not p.is_first_contact for p in self.participant_contexts
        )


class BriefNotification(BaseModel):
    """Schema for brief notification sent to Slack."""

    meeting_id: UUID
    meeting_title: str
    start_time: datetime
    duration_minutes: int
    participants: list[str]
    brief_content: str
    confidence: float
    location: Optional[str] = None
    hangout_link: Optional[str] = None
