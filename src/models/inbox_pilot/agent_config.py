"""InboxPilotConfig model for per-user agent configuration."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class InboxPilotConfig(Base):
    """Per-user InboxPilot configuration and preferences."""

    __tablename__ = "inbox_pilot_configs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key - one config per user
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Confidence thresholds
    escalation_threshold: Mapped[float] = mapped_column(Float, default=0.8)
    draft_threshold: Mapped[float] = mapped_column(Float, default=0.7)

    # Behavior preferences
    auto_archive_spam: Mapped[bool] = mapped_column(Boolean, default=True)
    draft_for_routine: Mapped[bool] = mapped_column(Boolean, default=True)
    escalate_urgent: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_send_high_confidence: Mapped[bool] = mapped_column(Boolean, default=False)

    # VIP contacts - always escalate regardless of classification
    vip_domains: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
    )
    vip_emails: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
    )

    # Ignored senders - skip processing entirely
    ignore_senders: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
    )
    ignore_domains: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
    )

    # Labels to watch (empty = all)
    watch_labels: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
    )

    # User signature for drafts
    email_signature: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Agent status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    paused_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pause_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Stats
    total_emails_processed: Mapped[int] = mapped_column(default=0)
    total_drafts_sent: Mapped[int] = mapped_column(default=0)
    total_escalations: Mapped[int] = mapped_column(default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<InboxPilotConfig user_id={self.user_id} active={self.is_active}>"

    def should_ignore_sender(self, sender_email: str) -> bool:
        """Check if sender should be ignored."""
        if sender_email in self.ignore_senders:
            return True

        domain = sender_email.split("@")[-1] if "@" in sender_email else ""
        if domain in self.ignore_domains:
            return True

        return False

    def is_vip_sender(self, sender_email: str) -> bool:
        """Check if sender is VIP (always escalate)."""
        if sender_email in self.vip_emails:
            return True

        domain = sender_email.split("@")[-1] if "@" in sender_email else ""
        if domain in self.vip_domains:
            return True

        return False
