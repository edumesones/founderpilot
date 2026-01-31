"""EmailRecord model for tracking processed emails."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class EmailRecord(Base):
    """Tracks processed emails for idempotency and audit."""

    __tablename__ = "email_records"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Gmail identifiers
    gmail_message_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    thread_id: Mapped[str] = mapped_column(String(255), index=True)

    # Email metadata
    sender: Mapped[str] = mapped_column(String(255))
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(500))
    snippet: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime)

    # Classification results
    category: Mapped[str] = mapped_column(String(50))  # urgent|important|routine|spam
    confidence: Mapped[float] = mapped_column(Float)
    classification_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing state
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        index=True,
    )  # pending|processing|escalated|completed|failed

    # Draft content (if generated)
    draft_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    draft_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    draft_tone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Action taken
    action_taken: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # sent|archived|rejected|ignored

    # Timestamps
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Audit trail
    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Human review details
    human_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    human_edited_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Indexes
    __table_args__ = (
        Index("idx_email_records_user_status", "user_id", "status"),
        Index("idx_email_records_user_received", "user_id", "received_at"),
    )

    def __repr__(self) -> str:
        return f"<EmailRecord {self.gmail_message_id} - {self.category}>"
