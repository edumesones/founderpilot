"""InvoicePilot agent - LangGraph implementation for invoice detection and reminders."""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph

from src.agents.invoice_pilot.nodes.detect import detect_invoice
from src.agents.invoice_pilot.nodes.extract import extract_data
from src.agents.invoice_pilot.nodes.scan import scan_inbox
from src.agents.invoice_pilot.state import (
    EscalationState,
    InvoiceState,
    ReminderState,
)
from src.core.llm import LLMRouter
from src.integrations.gmail.client import GmailClient
from src.integrations.slack.notifier import SlackNotifier


class InvoicePilotAgent:
    """LangGraph agent for invoice detection, tracking, and reminder automation.

    This agent manages three main workflows:

    1. Detection Flow (InvoiceState):
       - scan_inbox: Fetch sent emails with attachments
       - detect_invoice: LLM-based invoice detection
       - extract_data: Multimodal LLM extraction from PDF
       - confirm_invoice: Human confirmation if confidence < 80%
       - store_invoice: Save to database with audit trail

    2. Reminder Flow (ReminderState):
       - check_reminders_due: Daily check for invoices needing reminders
       - draft_reminder: Generate contextual reminder message
       - await_approval: Human approval via Slack
       - send_reminder: Send via Gmail API
       - log_action: Audit trail

    3. Escalation Flow (EscalationState):
       - detect_problem_pattern: Check for 3+ unanswered reminders
       - escalate_to_slack: Notify founder of payment issues
    """

    def __init__(
        self,
        gmail_client: GmailClient,
        slack_notifier: SlackNotifier,
        llm_router: LLMRouter,
        checkpointer: AsyncPostgresSaver,
        config: dict | None = None,
    ):
        """Initialize the agent.

        Args:
            gmail_client: Gmail API client for the user
            slack_notifier: Slack notification client
            llm_router: LLM provider router for detection/extraction/drafting
            checkpointer: LangGraph checkpointer for state persistence
            config: Agent configuration (thresholds, reminder schedule, etc.)
        """
        self.gmail = gmail_client
        self.slack = slack_notifier
        self.llm = llm_router
        self.checkpointer = checkpointer
        self.config = config or {}

        # Build the three workflows
        self.detection_graph = self._build_detection_graph()
        self.reminder_graph = self._build_reminder_graph()
        self.escalation_graph = self._build_escalation_graph()

    # ========================================================================
    # Detection Flow: Invoice Detection & Confirmation
    # ========================================================================

    def _build_detection_graph(self):
        """Build the invoice detection workflow.

        Graph structure:
        ```
        scan_inbox -> detect_invoice -> extract_data -> [routing]
                                                           |
                                       +-------------------+-------------------+
                                       |                                       |
                                  needs_confirmation                    store_invoice
                                       |                                       |
                                  confirm_invoice                             |
                                       |                                       |
                                  [approval] -> store_invoice                 |
                                       |              |                       |
                                       +-------+------+                       |
                                               v                              v
                                           audit_log <-----------------------+
                                               |
                                               v
                                              END
        ```
        """
        graph = StateGraph(InvoiceState)

        # Add nodes (stubs for now, will implement in T2.2)
        graph.add_node("scan_inbox", self._node_scan_inbox)
        graph.add_node("detect_invoice", self._node_detect_invoice)
        graph.add_node("extract_data", self._node_extract_data)
        graph.add_node("confirm_invoice", self._node_confirm_invoice)
        graph.add_node("store_invoice", self._node_store_invoice)
        graph.add_node("audit_log", self._node_audit_detection)

        # Set entry point
        graph.set_entry_point("scan_inbox")

        # Add edges
        graph.add_edge("scan_inbox", "detect_invoice")
        graph.add_edge("detect_invoice", "extract_data")

        # After extract: route based on confidence
        graph.add_conditional_edges(
            "extract_data",
            self._route_after_extract,
            {
                "confirm": "confirm_invoice",
                "store": "store_invoice",
            },
        )

        # Confirm always goes to store after human approval
        graph.add_edge("confirm_invoice", "store_invoice")

        # Store goes to audit
        graph.add_edge("store_invoice", "audit_log")

        # Audit ends the workflow
        graph.add_edge("audit_log", END)

        # Compile with checkpointer and interrupt before confirm
        return graph.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["confirm_invoice"],
        )

    # Detection node implementations

    async def _node_scan_inbox(self, state: InvoiceState) -> dict:
        """Scan inbox for sent emails with PDF attachments."""
        return await scan_inbox(state, self.gmail)

    async def _node_detect_invoice(self, state: InvoiceState) -> dict:
        """Detect if email contains an invoice using LLM."""
        return await detect_invoice(state, self.llm)

    async def _node_extract_data(self, state: InvoiceState) -> dict:
        """Extract invoice data from PDF using multimodal LLM."""
        return await extract_data(state, self.llm)

    async def _node_confirm_invoice(self, state: InvoiceState) -> dict:
        """Human confirmation node - this is an interrupt point."""
        return state

    async def _node_store_invoice(self, state: InvoiceState) -> dict:
        """Store invoice in database."""
        # TODO: Implement in T2.3
        return {
            "invoice_id": 1,
            "stored": True,
            "steps": state.get("steps", []) + [{
                "node": "store_invoice",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"invoice_id": 1},
                "error": None,
            }],
        }

    async def _node_audit_detection(self, state: InvoiceState) -> dict:
        """Audit log node for detection workflow."""
        step = {
            "node": "audit_log",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "invoice_id": state.get("invoice_id"),
                "stored": state.get("stored"),
                "total_steps": len(state.get("steps", [])),
            },
            "error": None,
        }
        return {
            "steps": state.get("steps", []) + [step],
        }

    def _route_after_extract(self, state: InvoiceState) -> Literal["confirm", "store"]:
        """Route after extraction based on confidence threshold."""
        extraction = state.get("extraction")

        if not extraction:
            return "confirm"

        confidence = extraction.get("confidence", 0)
        threshold = self.config.get("confidence_threshold", 0.8)

        # Low confidence or missing critical fields -> confirm
        if confidence < threshold:
            return "confirm"

        missing_fields = extraction.get("missing_fields", [])
        critical_fields = {"invoice_number", "client_name", "amount_total"}

        if any(field in critical_fields for field in missing_fields):
            return "confirm"

        # High confidence -> auto-store
        return "store"

    # ========================================================================
    # Reminder Flow: Reminder Scheduling & Sending
    # ========================================================================

    def _build_reminder_graph(self):
        """Build the reminder workflow.

        Graph structure:
        ```
        check_reminders_due -> draft_reminder -> await_approval -> send_reminder -> log_action -> END
        ```
        """
        graph = StateGraph(ReminderState)

        # Add nodes (stubs for now, will implement in T2.4)
        graph.add_node("check_reminders_due", self._node_check_reminders)
        graph.add_node("draft_reminder", self._node_draft_reminder)
        graph.add_node("await_approval", self._node_await_approval)
        graph.add_node("send_reminder", self._node_send_reminder)
        graph.add_node("log_action", self._node_log_reminder)

        # Set entry point
        graph.set_entry_point("check_reminders_due")

        # Linear flow
        graph.add_edge("check_reminders_due", "draft_reminder")
        graph.add_edge("draft_reminder", "await_approval")
        graph.add_edge("await_approval", "send_reminder")
        graph.add_edge("send_reminder", "log_action")
        graph.add_edge("log_action", END)

        # Compile with interrupt before approval
        return graph.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["await_approval"],
        )

    # Reminder node stubs (will implement in T2.4)

    async def _node_check_reminders(self, state: ReminderState) -> dict:
        """Check which reminders are due."""
        # TODO: Implement in T2.4
        return {
            "steps": state.get("steps", []) + [{
                "node": "check_reminders_due",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "stub"},
                "error": None,
            }],
        }

    async def _node_draft_reminder(self, state: ReminderState) -> dict:
        """Generate reminder message with LLM."""
        # TODO: Implement in T2.4
        return {
            "draft": {
                "subject": "Stub Reminder",
                "body": "This is a stub reminder.",
                "tone": "friendly",
                "confidence": 0.9,
            },
            "steps": state.get("steps", []) + [{
                "node": "draft_reminder",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "stub"},
                "error": None,
            }],
        }

    async def _node_await_approval(self, state: ReminderState) -> dict:
        """Wait for human approval - this is an interrupt point."""
        return state

    async def _node_send_reminder(self, state: ReminderState) -> dict:
        """Send reminder via Gmail API."""
        # TODO: Implement in T2.4
        return {
            "sent": True,
            "sent_message_id": "stub_message_id",
            "steps": state.get("steps", []) + [{
                "node": "send_reminder",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"sent": True},
                "error": None,
            }],
        }

    async def _node_log_reminder(self, state: ReminderState) -> dict:
        """Log reminder action to audit trail."""
        step = {
            "node": "log_action",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "reminder_id": state.get("reminder_id"),
                "sent": state.get("sent"),
            },
            "error": None,
        }
        return {
            "steps": state.get("steps", []) + [step],
        }

    # ========================================================================
    # Escalation Flow: Problem Pattern Detection
    # ========================================================================

    def _build_escalation_graph(self):
        """Build the escalation workflow.

        Graph structure:
        ```
        detect_problem_pattern -> escalate_to_slack -> END
        ```
        """
        graph = StateGraph(EscalationState)

        # Add nodes (stubs for now, will implement in T2.5)
        graph.add_node("detect_problem_pattern", self._node_detect_problem)
        graph.add_node("escalate_to_slack", self._node_escalate)

        # Set entry point
        graph.set_entry_point("detect_problem_pattern")

        # Linear flow
        graph.add_edge("detect_problem_pattern", "escalate_to_slack")
        graph.add_edge("escalate_to_slack", END)

        # Compile (no interrupts needed for escalation)
        return graph.compile(checkpointer=self.checkpointer)

    # Escalation node stubs (will implement in T2.5)

    async def _node_detect_problem(self, state: EscalationState) -> dict:
        """Detect problem patterns in invoice history."""
        # TODO: Implement in T2.5
        return {
            "steps": state.get("steps", []) + [{
                "node": "detect_problem_pattern",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "stub"},
                "error": None,
            }],
        }

    async def _node_escalate(self, state: EscalationState) -> dict:
        """Escalate to Slack with problem details."""
        # TODO: Implement in T2.5
        return {
            "escalated": True,
            "slack_message_id": "stub_slack_id",
            "steps": state.get("steps", []) + [{
                "node": "escalate_to_slack",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"escalated": True},
                "error": None,
            }],
        }

    # ========================================================================
    # Public API
    # ========================================================================

    async def run_detection(self, gmail_message_id: str, tenant_id: str) -> InvoiceState:
        """Run invoice detection workflow for a single email.

        Args:
            gmail_message_id: Gmail message ID to process
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            Final state after detection workflow
        """
        initial_state: InvoiceState = {
            "gmail_message_id": gmail_message_id,
            "tenant_id": tenant_id,
            "config": self.config,
            "detection": None,
            "extraction": None,
            "needs_confirmation": False,
            "human_decision": None,
            "edited_data": None,
            "invoice_id": None,
            "stored": False,
            "error": None,
            "trace_id": str(uuid4()),
            "steps": [],
        }

        config = {"configurable": {"thread_id": f"detection_{gmail_message_id}"}}
        result = await self.detection_graph.ainvoke(initial_state, config)
        return result

    async def run_reminder(self, invoice_id: int, tenant_id: str) -> ReminderState:
        """Run reminder workflow for a single invoice.

        Args:
            invoice_id: Invoice ID to send reminder for
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            Final state after reminder workflow
        """
        initial_state: ReminderState = {
            "invoice_id": invoice_id,
            "tenant_id": tenant_id,
            "reminder_id": None,
            "config": self.config,
            "invoice_data": None,
            "days_overdue": 0,
            "reminder_count": 0,
            "draft": None,
            "needs_approval": True,
            "human_decision": None,
            "edited_draft": None,
            "sent": False,
            "sent_message_id": None,
            "error": None,
            "trace_id": str(uuid4()),
            "steps": [],
        }

        config = {"configurable": {"thread_id": f"reminder_{invoice_id}"}}
        result = await self.reminder_graph.ainvoke(initial_state, config)
        return result

    async def run_escalation(self, invoice_id: int, tenant_id: str) -> EscalationState:
        """Run escalation workflow for problem invoices.

        Args:
            invoice_id: Invoice ID with payment issues
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            Final state after escalation workflow
        """
        initial_state: EscalationState = {
            "invoice_id": invoice_id,
            "tenant_id": tenant_id,
            "invoice_data": {},
            "reminder_history": [],
            "pattern_type": "repeated_reminders",
            "escalated": False,
            "slack_message_id": None,
            "error": None,
            "trace_id": str(uuid4()),
            "steps": [],
        }

        config = {"configurable": {"thread_id": f"escalation_{invoice_id}"}}
        result = await self.escalation_graph.ainvoke(initial_state, config)
        return result

    async def resume_detection(
        self,
        gmail_message_id: str,
        human_decision: Literal["confirm", "reject", "edit"],
        edited_data: dict | None = None,
    ) -> InvoiceState:
        """Resume detection workflow after human confirmation.

        Args:
            gmail_message_id: Gmail message ID (used as thread_id)
            human_decision: Human decision on the detected invoice
            edited_data: Edited invoice data (only for 'edit' action)

        Returns:
            Final state after resuming
        """
        config = {"configurable": {"thread_id": f"detection_{gmail_message_id}"}}

        update = {
            "human_decision": human_decision,
            "edited_data": edited_data,
        }

        result = await self.detection_graph.ainvoke(update, config)
        return result

    async def resume_reminder(
        self,
        invoice_id: int,
        human_decision: Literal["approve", "edit", "skip"],
        edited_draft: dict | None = None,
    ) -> ReminderState:
        """Resume reminder workflow after human approval.

        Args:
            invoice_id: Invoice ID (used as thread_id)
            human_decision: Human decision on the reminder
            edited_draft: Edited draft content (only for 'edit' action)

        Returns:
            Final state after resuming
        """
        config = {"configurable": {"thread_id": f"reminder_{invoice_id}"}}

        update = {
            "human_decision": human_decision,
            "edited_draft": edited_draft,
        }

        result = await self.reminder_graph.ainvoke(update, config)
        return result
