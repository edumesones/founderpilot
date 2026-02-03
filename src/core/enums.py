"""Core enumerations for the application."""
from enum import Enum


class AgentType(str, Enum):
    """Agent types for usage tracking and audit logging."""

    INBOX = "inbox"
    INVOICE = "invoice"
    MEETING = "meeting"


class ActionType(str, Enum):
    """Action types for usage tracking events."""

    # InboxPilot actions
    EMAIL_PROCESSED = "email_processed"
    EMAIL_DRAFTED = "email_drafted"
    EMAIL_CLASSIFIED = "email_classified"

    # InvoicePilot actions
    INVOICE_DETECTED = "invoice_detected"
    INVOICE_TRACKED = "invoice_tracked"
    INVOICE_REMINDER_SENT = "invoice_reminder_sent"

    # MeetingPilot actions
    MEETING_PREP = "meeting_prep"
    MEETING_NOTES = "meeting_notes"
    MEETING_FOLLOWUP = "meeting_followup"
