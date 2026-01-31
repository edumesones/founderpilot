"""InboxPilot configuration schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InboxPilotConfigResponse(BaseModel):
    """Response schema for InboxPilot configuration."""

    id: UUID
    user_id: UUID

    # Thresholds
    escalation_threshold: float = Field(ge=0.0, le=1.0)
    draft_threshold: float = Field(ge=0.0, le=1.0)

    # Behavior
    auto_archive_spam: bool
    draft_for_routine: bool
    escalate_urgent: bool
    auto_send_high_confidence: bool

    # VIP contacts
    vip_domains: list[str]
    vip_emails: list[str]

    # Ignored senders
    ignore_senders: list[str]
    ignore_domains: list[str]

    # Labels to watch
    watch_labels: list[str]

    # Signature
    email_signature: Optional[str] = None

    # Status
    is_active: bool
    paused_until: Optional[datetime] = None
    pause_reason: Optional[str] = None

    # Stats
    total_emails_processed: int
    total_drafts_sent: int
    total_escalations: int

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InboxPilotConfigUpdate(BaseModel):
    """Request schema for updating InboxPilot configuration."""

    # Thresholds
    escalation_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    draft_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Behavior
    auto_archive_spam: Optional[bool] = None
    draft_for_routine: Optional[bool] = None
    escalate_urgent: Optional[bool] = None
    auto_send_high_confidence: Optional[bool] = None

    # VIP contacts
    vip_domains: Optional[list[str]] = None
    vip_emails: Optional[list[str]] = None

    # Ignored senders
    ignore_senders: Optional[list[str]] = None
    ignore_domains: Optional[list[str]] = None

    # Labels to watch
    watch_labels: Optional[list[str]] = None

    # Signature
    email_signature: Optional[str] = Field(None, max_length=1000)

    # Status
    is_active: Optional[bool] = None


class InboxPilotConfigCreate(BaseModel):
    """Schema for creating default InboxPilot configuration."""

    user_id: UUID

    # Optional overrides from defaults
    escalation_threshold: float = 0.8
    draft_threshold: float = 0.7
    auto_archive_spam: bool = True
    draft_for_routine: bool = True
    escalate_urgent: bool = True
    auto_send_high_confidence: bool = False


class WatchSetupResponse(BaseModel):
    """Response schema for Gmail watch setup."""

    success: bool
    history_id: str
    expiration: datetime
    message: Optional[str] = None
