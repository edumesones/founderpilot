"""Pydantic schemas for API request/response validation."""

from src.schemas.inbox_pilot.email import (
    EmailResponse,
    EmailListResponse,
    EmailActionRequest,
    EmailActionResponse,
)
from src.schemas.inbox_pilot.config import (
    InboxPilotConfigResponse,
    InboxPilotConfigUpdate,
)
from src.schemas.inbox_pilot.classification import (
    ClassificationResult,
    DraftResult,
)

__all__ = [
    "EmailResponse",
    "EmailListResponse",
    "EmailActionRequest",
    "EmailActionResponse",
    "InboxPilotConfigResponse",
    "InboxPilotConfigUpdate",
    "ClassificationResult",
    "DraftResult",
]
