"""
Agent Audit Log model for tracking AI agent actions.

This model stores audit trails for InboxPilot, InvoicePilot, and MeetingPilot
actions, including confidence levels, input/output data, and escalation status.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDMixin


class AgentAuditLog(Base, UUIDMixin, TimestampMixin):
    """
    Audit log model for tracking AI agent actions.

    Attributes:
        id: Unique identifier (UUID)
        timestamp: When the action occurred
        user_id: FK to the user who owns this workflow
        workflow_id: LangGraph workflow run ID
        agent_type: Type of agent (inbox_pilot, invoice_pilot, meeting_pilot)
        action: Action performed (classify_email, draft_response, send_reminder, etc.)
        input_summary: Truncated input (max 2000 chars)
        output_summary: Truncated output (max 2000 chars)
        decision: Human-readable decision made by the agent
        confidence: Confidence level (0.0 to 1.0)
        escalated: Whether the action was escalated for human approval
        authorized_by: Who authorized the action ('agent' or user_id)
        trace_id: Langfuse trace ID for detailed debugging
        metadata: Full input/output and extra context (JSONB)
        rolled_back: Whether this action has been rolled back
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """

    __tablename__ = "agent_audit_logs"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    agent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    input_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    output_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    decision: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    escalated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    authorized_by: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    rolled_back: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range_check",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AgentAuditLog(id={self.id}, "
            f"agent_type={self.agent_type}, "
            f"action={self.action}, "
            f"user_id={self.user_id})>"
        )


# Agent type constants
class AgentType:
    """Constants for agent types."""

    INBOX_PILOT = "inbox_pilot"
    INVOICE_PILOT = "invoice_pilot"
    MEETING_PILOT = "meeting_pilot"


# Action constants for InboxPilot
class InboxPilotAction:
    """Constants for InboxPilot actions."""

    CLASSIFY_EMAIL = "classify_email"
    DRAFT_RESPONSE = "draft_response"
    SEND_RESPONSE = "send_response"
    ARCHIVE_EMAIL = "archive_email"
    FLAG_EMAIL = "flag_email"
    ESCALATE_TO_HUMAN = "escalate_to_human"


# Action constants for InvoicePilot
class InvoicePilotAction:
    """Constants for InvoicePilot actions."""

    DETECT_INVOICE = "detect_invoice"
    EXTRACT_INVOICE_DATA = "extract_invoice_data"
    MATCH_INVOICE = "match_invoice"
    SEND_REMINDER = "send_reminder"
    ESCALATE_TO_HUMAN = "escalate_to_human"


# Action constants for MeetingPilot
class MeetingPilotAction:
    """Constants for MeetingPilot actions."""

    SCHEDULE_MEETING = "schedule_meeting"
    SEND_REMINDER = "send_reminder"
    RESCHEDULE_MEETING = "reschedule_meeting"
    CANCEL_MEETING = "cancel_meeting"
    ESCALATE_TO_HUMAN = "escalate_to_human"
