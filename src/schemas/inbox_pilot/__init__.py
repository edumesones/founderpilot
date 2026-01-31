"""InboxPilot schemas."""

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
    EmailData,
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
    "EmailData",
]
