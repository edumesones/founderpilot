"""MeetingPilot configuration Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MeetingPilotConfigCreate(BaseModel):
    """Schema for creating a MeetingPilot config."""

    is_enabled: bool = True
    brief_minutes_before: int = Field(default=30, ge=5, le=120)
    only_external_meetings: bool = True
    min_attendees: int = Field(default=1, ge=1, le=50)
    escalation_threshold: Decimal = Field(default=Decimal("0.80"), ge=0, le=1)


class MeetingPilotConfigUpdate(BaseModel):
    """Schema for updating a MeetingPilot config."""

    is_enabled: Optional[bool] = None
    brief_minutes_before: Optional[int] = Field(default=None, ge=5, le=120)
    only_external_meetings: Optional[bool] = None
    min_attendees: Optional[int] = Field(default=None, ge=1, le=50)
    escalation_threshold: Optional[Decimal] = Field(default=None, ge=0, le=1)


class MeetingPilotConfigResponse(BaseModel):
    """Schema for MeetingPilot config API response."""

    id: UUID
    user_id: UUID
    is_enabled: bool
    brief_minutes_before: int
    only_external_meetings: bool
    min_attendees: int
    escalation_threshold: Decimal
    total_meetings_processed: int
    total_briefs_sent: int
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
