"""MeetingPilot Pydantic schemas."""

from src.schemas.meeting_pilot.brief import (
    BriefGenerationRequest,
    BriefResult,
)
from src.schemas.meeting_pilot.config import (
    MeetingPilotConfigCreate,
    MeetingPilotConfigResponse,
    MeetingPilotConfigUpdate,
)
from src.schemas.meeting_pilot.meeting import (
    AttendeeData,
    MeetingListResponse,
    MeetingNoteCreate,
    MeetingNoteResponse,
    MeetingRecordCreate,
    MeetingRecordResponse,
)

__all__ = [
    # Meeting
    "AttendeeData",
    "MeetingRecordCreate",
    "MeetingRecordResponse",
    "MeetingListResponse",
    "MeetingNoteCreate",
    "MeetingNoteResponse",
    # Brief
    "BriefGenerationRequest",
    "BriefResult",
    # Config
    "MeetingPilotConfigCreate",
    "MeetingPilotConfigUpdate",
    "MeetingPilotConfigResponse",
]
