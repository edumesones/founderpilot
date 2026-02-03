"""State definition for InvoicePilot agent."""

from datetime import datetime
from typing import Literal, Optional, TypedDict


class InvoiceData(TypedDict):
    """Extracted invoice data from PDF."""

    invoice_number: Optional[str]
    client_name: Optional[str]
    client_email: Optional[str]
    amount_total: Optional[float]
    currency: Optional[str]
    issue_date: Optional[datetime]
    due_date: Optional[datetime]
    line_items: Optional[list[dict]]


class DetectionResult(TypedDict):
    """Result of invoice detection in email."""

    is_invoice: bool
    confidence: float
    reasoning: str
    gmail_message_id: str
    pdf_url: Optional[str]


class ExtractionResult(TypedDict):
    """Result of invoice data extraction."""

    data: InvoiceData
    confidence: float
    missing_fields: list[str]


class ReminderDraft(TypedDict):
    """Generated reminder message draft."""

    subject: str
    body: str
    tone: Literal["friendly", "professional", "firm"]
    confidence: float


class AgentStep(TypedDict):
    """Record of a single step in the agent workflow."""

    node: str
    timestamp: str
    result: Optional[dict]
    error: Optional[str]


class InvoiceState(TypedDict):
    """Complete state for InvoicePilot agent workflow.

    This is the main state object that flows through the LangGraph.
    Used for invoice detection and confirmation flow.
    """

    # Input
    gmail_message_id: str
    tenant_id: str

    # Configuration
    config: Optional[dict]

    # Detection
    detection: Optional[DetectionResult]

    # Extraction
    extraction: Optional[ExtractionResult]

    # Confirmation
    needs_confirmation: bool
    human_decision: Optional[Literal["confirm", "reject", "edit"]]
    edited_data: Optional[InvoiceData]

    # Storage
    invoice_id: Optional[int]
    stored: bool

    # Error handling
    error: Optional[str]

    # Audit
    trace_id: str
    steps: list[AgentStep]


class ReminderState(TypedDict):
    """State for reminder generation and sending workflow.

    Used for the reminder scheduling and approval flow.
    """

    # Input
    invoice_id: int
    tenant_id: str
    reminder_id: Optional[int]

    # Configuration
    config: Optional[dict]

    # Invoice context
    invoice_data: Optional[dict]
    days_overdue: int
    reminder_count: int

    # Draft
    draft: Optional[ReminderDraft]

    # Approval
    needs_approval: bool
    human_decision: Optional[Literal["approve", "edit", "skip"]]
    edited_draft: Optional[ReminderDraft]

    # Sending
    sent: bool
    sent_message_id: Optional[str]

    # Error handling
    error: Optional[str]

    # Audit
    trace_id: str
    steps: list[AgentStep]


class EscalationState(TypedDict):
    """State for problem pattern escalation workflow.

    Used when an invoice has too many unanswered reminders.
    """

    # Input
    invoice_id: int
    tenant_id: str

    # Problem context
    invoice_data: dict
    reminder_history: list[dict]
    pattern_type: Literal["repeated_reminders", "high_amount", "vip_client"]

    # Escalation
    escalated: bool
    slack_message_id: Optional[str]

    # Error handling
    error: Optional[str]

    # Audit
    trace_id: str
    steps: list[AgentStep]
