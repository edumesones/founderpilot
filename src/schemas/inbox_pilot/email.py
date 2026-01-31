"""Email-related Pydantic schemas."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EmailResponse(BaseModel):
    """Response schema for a single processed email."""

    id: UUID
    gmail_message_id: str
    thread_id: str

    # Email metadata
    sender: str
    sender_name: Optional[str] = None
    subject: str
    snippet: Optional[str] = None
    received_at: datetime

    # Classification
    category: Literal["urgent", "important", "routine", "spam"]
    confidence: float = Field(ge=0.0, le=1.0)

    # Status
    status: Literal["pending", "processing", "escalated", "completed", "failed"]

    # Draft
    draft_content: Optional[str] = None
    draft_confidence: Optional[float] = None

    # Action
    action_taken: Optional[Literal["sent", "archived", "rejected", "ignored"]] = None

    # Timestamps
    processed_at: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    """Response schema for paginated email list."""

    items: list[EmailResponse]
    total: int
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=100)
    has_more: bool


class EmailActionRequest(BaseModel):
    """Request schema for taking action on an email."""

    action: Literal["approve", "reject", "archive", "edit"]
    edited_content: Optional[str] = Field(
        None,
        description="Edited draft content (only for 'edit' action)",
    )


class EmailActionResponse(BaseModel):
    """Response schema after taking action on an email."""

    success: bool
    action_taken: Literal["sent", "archived", "rejected", "ignored"]
    message: Optional[str] = None


class EmailWebhookPayload(BaseModel):
    """Schema for Gmail Pub/Sub webhook payload."""

    message: dict
    subscription: str


class GmailHistoryNotification(BaseModel):
    """Parsed Gmail history notification from Pub/Sub."""

    email_address: str
    history_id: str
