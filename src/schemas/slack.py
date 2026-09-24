"""Pydantic schemas for Slack integration."""
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================================================
# Installation Schemas
# ============================================================================

class SlackInstallationCreate(BaseModel):
    """Schema for creating a Slack installation from OAuth callback."""
    team_id: str
    team_name: Optional[str] = None
    enterprise_id: Optional[str] = None
    bot_user_id: str
    bot_access_token: str
    user_access_token: Optional[str] = None
    user_slack_id: Optional[str] = None
    scopes: Optional[str] = None


class SlackInstallationResponse(BaseModel):
    """Response schema for Slack installation details."""
    id: UUID
    team_id: str
    team_name: Optional[str]
    bot_user_id: str
    dm_channel_id: Optional[str]
    installed_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class SlackStatusResponse(BaseModel):
    """Response schema for Slack connection status."""
    connected: bool
    team_name: Optional[str] = None
    team_id: Optional[str] = None
    installed_at: Optional[datetime] = None


class SlackOAuthCallbackResponse(BaseModel):
    """Response schema for successful OAuth callback."""
    status: Literal["connected"] = "connected"
    team_name: str
    bot_user_id: str


# ============================================================================
# Notification Payloads
# ============================================================================

class NotificationPayload(BaseModel):
    """Base schema for notification payloads."""
    workflow_id: UUID
    notification_type: str


class EmailNotificationPayload(NotificationPayload):
    """Payload for email action notifications."""
    notification_type: Literal["email"] = "email"
    sender: str
    subject: str
    classification: str  # URGENT, ACTIONABLE, FYI, SPAM
    confidence: int = Field(ge=0, le=100)  # 0-100%
    proposed_response: str
    email_snippet: Optional[str] = None  # Preview of email content


class InvoiceNotificationPayload(NotificationPayload):
    """Payload for invoice notifications."""
    notification_type: Literal["invoice"] = "invoice"
    client_name: str
    invoice_number: str
    amount: str  # Formatted string like "$1,500.00"
    due_date: str
    days_overdue: Optional[int] = None
    proposed_action: str  # e.g., "Send reminder email"


class MeetingNotificationPayload(NotificationPayload):
    """Payload for meeting prep notifications."""
    notification_type: Literal["meeting"] = "meeting"
    meeting_title: str
    start_time: datetime
    attendees: list[str]
    context_summary: str
    proposed_prep: str  # Suggested preparation points


# ============================================================================
# Action Results
# ============================================================================

class ActionResult(BaseModel):
    """Result of a Slack action (button click)."""
    success: bool
    workflow_id: UUID
    action: str  # approve, reject, edit, snooze
    summary: str  # Human-readable summary
    timestamp: datetime
    error: Optional[str] = None


# ============================================================================
# Webhook Payloads
# ============================================================================

class SlackEventPayload(BaseModel):
    """Incoming Slack event webhook payload."""
    token: str
    team_id: str
    type: str
    event: Optional[dict] = None
    challenge: Optional[str] = None  # URL verification


class SlackInteractivePayload(BaseModel):
    """Incoming Slack interactive component payload."""
    type: str
    user: dict
    container: dict
    actions: list[dict]
    response_url: str
    trigger_id: str
