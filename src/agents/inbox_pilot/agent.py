"""InboxPilot agent - LangGraph implementation for email triage."""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph

from src.agents.inbox_pilot.nodes.classify import classify_email
from src.agents.inbox_pilot.nodes.draft import draft_response
from src.agents.inbox_pilot.nodes.escalate import escalate_to_human
from src.agents.inbox_pilot.nodes.execute import execute_action
from src.agents.inbox_pilot.nodes.fetch import fetch_email
from src.agents.inbox_pilot.state import InboxState
from src.core.llm import LLMRouter
from src.integrations.gmail.client import GmailClient
from src.integrations.slack.notifier import SlackNotifier
from src.models.inbox_pilot.agent_config import InboxPilotConfig


class InboxPilotAgent:
    """LangGraph agent for email triage and response.

    This agent processes incoming emails through a state machine:
    1. Fetch: Get full email data from Gmail
    2. Classify: Categorize as urgent/important/routine/spam
    3. Draft: Generate response for routine emails
    4. Escalate: Notify human via Slack when needed
    5. Execute: Send response or archive email

    Human-in-the-loop is implemented via LangGraph's interrupt_before
    mechanism on the human_review node.
    """

    def __init__(
        self,
        gmail_client: GmailClient,
        slack_notifier: SlackNotifier,
        llm_router: LLMRouter,
        user_config: InboxPilotConfig,
        checkpointer: AsyncPostgresSaver,
    ):
        """Initialize the agent.

        Args:
            gmail_client: Gmail API client for the user
            slack_notifier: Slack notification client
            llm_router: LLM provider router for classification/drafting
            user_config: User's InboxPilot configuration
            checkpointer: LangGraph checkpointer for state persistence
        """
        self.gmail = gmail_client
        self.slack = slack_notifier
        self.llm = llm_router
        self.config = user_config
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph state machine.

        Graph structure:
        ```
        fetch_email -> classify -> [routing] -> draft_response -> [routing] -> escalate
                                       |                              |            |
                                       v                              v            v
                                   execute <--------------------------+      human_review
                                       |                                         |
                                       v                                         v
                                   audit_log <----------------------------------+
                                       |
                                       v
                                      END
        ```
        """
        # Create the graph with our state type
        graph = StateGraph(InboxState)

        # Add nodes
        graph.add_node("fetch_email", self._node_fetch)
        graph.add_node("classify", self._node_classify)
        graph.add_node("draft_response", self._node_draft)
        graph.add_node("escalate", self._node_escalate)
        graph.add_node("human_review", self._node_human_review)
        graph.add_node("execute_action", self._node_execute)
        graph.add_node("audit_log", self._node_audit)

        # Set entry point
        graph.set_entry_point("fetch_email")

        # Add edges
        graph.add_edge("fetch_email", "classify")

        # After classify: route based on category and confidence
        graph.add_conditional_edges(
            "classify",
            self._route_after_classify,
            {
                "draft": "draft_response",
                "escalate": "escalate",
                "archive": "execute_action",
            },
        )

        # After draft: route based on draft confidence
        graph.add_conditional_edges(
            "draft_response",
            self._route_after_draft,
            {
                "escalate": "escalate",
                "auto_send": "execute_action",
            },
        )

        # Escalate always goes to human_review
        graph.add_edge("escalate", "human_review")

        # Human review goes to execute
        graph.add_edge("human_review", "execute_action")

        # Execute goes to audit
        graph.add_edge("execute_action", "audit_log")

        # Audit ends the workflow
        graph.add_edge("audit_log", END)

        # Compile with checkpointer and interrupt before human_review
        return graph.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["human_review"],
        )

    # Node implementations - wrap the actual functions with dependencies

    async def _node_fetch(self, state: InboxState) -> dict:
        """Fetch email node wrapper."""
        return await fetch_email(state, self.gmail)

    async def _node_classify(self, state: InboxState) -> dict:
        """Classify email node wrapper."""
        return await classify_email(state, self.llm)

    async def _node_draft(self, state: InboxState) -> dict:
        """Draft response node wrapper."""
        signature = self.config.email_signature if self.config else None
        return await draft_response(state, self.llm, signature)

    async def _node_escalate(self, state: InboxState) -> dict:
        """Escalate to human node wrapper."""
        return await escalate_to_human(state, self.slack)

    async def _node_human_review(self, state: InboxState) -> dict:
        """Human review node - this is an interrupt point.

        The workflow pauses here until resume() is called with human input.
        """
        return state

    async def _node_execute(self, state: InboxState) -> dict:
        """Execute action node wrapper."""
        return await execute_action(state, self.gmail)

    async def _node_audit(self, state: InboxState) -> dict:
        """Audit log node - records the final state.

        Actual audit logging is handled by the service layer.
        """
        step = {
            "node": "audit_log",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "action_taken": state.get("action_taken"),
                "total_steps": len(state.get("steps", [])),
            },
            "error": None,
        }
        return {
            "steps": state.get("steps", []) + [step],
        }

    # Routing functions

    def _route_after_classify(
        self, state: InboxState
    ) -> Literal["draft", "escalate", "archive"]:
        """Route after classification based on category and config."""
        classification = state.get("classification")
        email = state.get("email")

        if not classification:
            return "escalate"

        category = classification.get("category")
        confidence = classification.get("confidence", 0)

        # Check VIP - always escalate
        if email and self.config:
            sender = email.get("sender", "")
            if self.config.is_vip_sender(sender):
                return "escalate"

        # Low confidence - escalate
        escalation_threshold = (
            self.config.escalation_threshold if self.config else 0.8
        )
        if confidence < escalation_threshold:
            return "escalate"

        # Route by category
        if category == "urgent":
            return "escalate"

        if category == "spam":
            auto_archive = self.config.auto_archive_spam if self.config else True
            return "archive" if auto_archive else "escalate"

        if category == "routine":
            draft_enabled = self.config.draft_for_routine if self.config else True
            return "draft" if draft_enabled else "archive"

        # important -> escalate
        return "escalate"

    def _route_after_draft(
        self, state: InboxState
    ) -> Literal["escalate", "auto_send"]:
        """Route after draft generation based on confidence."""
        draft = state.get("draft")
        classification = state.get("classification")

        if not draft:
            return "escalate"

        draft_confidence = draft.get("confidence", 0)
        draft_threshold = self.config.draft_threshold if self.config else 0.7

        # Low confidence draft - escalate
        if draft_confidence < draft_threshold:
            return "escalate"

        # Check if auto-send is enabled and confidence is very high
        auto_send_enabled = (
            self.config.auto_send_high_confidence if self.config else False
        )
        category = classification.get("category") if classification else None

        if auto_send_enabled and draft_confidence >= 0.9 and category == "routine":
            return "auto_send"

        # Default: escalate for human approval
        return "escalate"

    # Public API

    async def run(self, message_id: str) -> InboxState:
        """Run the agent for a single email.

        Args:
            message_id: Gmail message ID to process

        Returns:
            Final agent state after processing
        """
        # Create initial state
        initial_state: InboxState = {
            "message_id": message_id,
            "user_id": str(self.config.user_id) if self.config else "",
            "config": self._config_to_dict(),
            "email": None,
            "classification": None,
            "draft": None,
            "needs_human_review": False,
            "human_decision": None,
            "edited_content": None,
            "action_taken": None,
            "error": None,
            "trace_id": str(uuid4()),
            "steps": [],
        }

        # Configure with message_id as thread_id for checkpointing
        config = {"configurable": {"thread_id": message_id}}

        # Run the graph
        result = await self.graph.ainvoke(initial_state, config)
        return result

    async def resume(
        self,
        message_id: str,
        human_decision: Literal["approve", "reject", "edit", "archive"],
        edited_content: str | None = None,
    ) -> InboxState:
        """Resume the workflow after human review.

        Args:
            message_id: Gmail message ID (used as thread_id)
            human_decision: The human's decision on the email
            edited_content: Edited draft content (only for 'edit' action)

        Returns:
            Final agent state after resuming
        """
        config = {"configurable": {"thread_id": message_id}}

        # Get current state
        current_state = await self.graph.aget_state(config)

        # Update with human input
        update = {
            "human_decision": human_decision,
            "edited_content": edited_content,
        }

        # Resume execution
        result = await self.graph.ainvoke(update, config)
        return result

    async def get_state(self, message_id: str) -> InboxState | None:
        """Get the current state for a message.

        Args:
            message_id: Gmail message ID (used as thread_id)

        Returns:
            Current state or None if not found
        """
        config = {"configurable": {"thread_id": message_id}}
        state = await self.graph.aget_state(config)
        return state.values if state else None

    def _config_to_dict(self) -> dict | None:
        """Convert user config to dict for state."""
        if not self.config:
            return None

        return {
            "escalation_threshold": self.config.escalation_threshold,
            "draft_threshold": self.config.draft_threshold,
            "auto_archive_spam": self.config.auto_archive_spam,
            "draft_for_routine": self.config.draft_for_routine,
            "escalate_urgent": self.config.escalate_urgent,
            "auto_send_high_confidence": self.config.auto_send_high_confidence,
            "vip_domains": list(self.config.vip_domains),
            "vip_emails": list(self.config.vip_emails),
        }
