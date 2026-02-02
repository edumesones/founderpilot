"""MeetingPilot agent - LangGraph implementation for meeting preparation."""

from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph

from src.agents.meeting_pilot.nodes.brief import generate_brief
from src.agents.meeting_pilot.nodes.context import gather_context
from src.agents.meeting_pilot.nodes.fetch import fetch_meeting
from src.agents.meeting_pilot.nodes.followup import suggest_followup
from src.agents.meeting_pilot.nodes.notes import capture_notes
from src.agents.meeting_pilot.nodes.notify import notify_slack
from src.agents.meeting_pilot.prompts import BRIEF_SYSTEM_PROMPT
from src.agents.meeting_pilot.state import MeetingState
from src.core.llm import LLMRouter
from src.integrations.gmail.client import GmailClient
from src.integrations.slack.notifier import SlackNotifier
from src.models.meeting_pilot.agent_config import MeetingPilotConfig
from src.models.meeting_pilot.meeting_record import MeetingRecord


class MeetingPilotAgent:
    """LangGraph agent for meeting preparation.

    This agent processes upcoming meetings through a state machine:
    1. Fetch: Get meeting data from database
    2. Gather Context: Query email history for participants
    3. Generate Brief: Create contextual meeting brief with LLM
    4. Notify: Send brief to user via Slack
    5. Human Review: Wait for meeting to complete (interrupt point)
    6. Capture Notes: Process post-meeting notes
    7. Suggest Follow-up: Generate action items
    8. Audit: Log all actions

    Human-in-the-loop is implemented via LangGraph's interrupt_before
    mechanism on the human_review node.
    """

    def __init__(
        self,
        gmail_client: GmailClient,
        slack_notifier: SlackNotifier,
        llm_router: LLMRouter,
        user_config: MeetingPilotConfig,
        checkpointer: AsyncPostgresSaver,
    ):
        """Initialize the agent.

        Args:
            gmail_client: Gmail API client for email context
            slack_notifier: Slack notification client
            llm_router: LLM provider router for brief generation
            user_config: User's MeetingPilot configuration
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
        fetch_meeting -> gather_context -> generate_brief -> [routing]
                                                              |
                                              +--------------+-------------+
                                              |                            |
                                              v                            v
                                         notify_slack              (escalate path)
                                              |                            |
                                              v                            |
                                         human_review <--------------------+
                                              |
                                              v
                                         capture_notes
                                              |
                                              v
                                         suggest_followup
                                              |
                                              v
                                          audit_log
                                              |
                                              v
                                             END
        ```
        """
        # Create the graph with our state type
        graph = StateGraph(MeetingState)

        # Add nodes
        graph.add_node("fetch_meeting", self._node_fetch)
        graph.add_node("gather_context", self._node_gather_context)
        graph.add_node("generate_brief", self._node_generate_brief)
        graph.add_node("notify_slack", self._node_notify)
        graph.add_node("human_review", self._node_human_review)
        graph.add_node("capture_notes", self._node_capture_notes)
        graph.add_node("suggest_followup", self._node_suggest_followup)
        graph.add_node("audit_log", self._node_audit)

        # Set entry point
        graph.set_entry_point("fetch_meeting")

        # Add edges
        graph.add_edge("fetch_meeting", "gather_context")
        graph.add_edge("gather_context", "generate_brief")

        # After brief: route based on confidence
        graph.add_conditional_edges(
            "generate_brief",
            self._route_after_brief,
            {
                "notify": "notify_slack",
                "error": "audit_log",
            },
        )

        # Notify goes to human review (interrupt point)
        graph.add_edge("notify_slack", "human_review")

        # Human review goes to capture notes
        graph.add_edge("human_review", "capture_notes")

        # Capture notes goes to suggest followup
        graph.add_edge("capture_notes", "suggest_followup")

        # Suggest followup goes to audit
        graph.add_edge("suggest_followup", "audit_log")

        # Audit ends the workflow
        graph.add_edge("audit_log", END)

        # Compile with checkpointer and interrupt before human_review
        return graph.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["human_review"],
        )

    # Node implementations

    async def _node_fetch(self, state: MeetingState) -> dict:
        """Fetch meeting node wrapper."""
        # In production, fetch from DB. For now, expect meeting_record in state
        meeting_record = state.get("_meeting_record")
        if meeting_record:
            return await fetch_meeting(state, meeting_record)
        return {
            "error": "No meeting record provided",
            "status": "error",
        }

    async def _node_gather_context(self, state: MeetingState) -> dict:
        """Gather context node wrapper."""
        max_emails = 5
        if self.config:
            max_emails = 5  # Could be configurable
        return await gather_context(state, self.gmail, max_emails)

    async def _node_generate_brief(self, state: MeetingState) -> dict:
        """Generate brief node wrapper."""
        return await generate_brief(state, self.llm, BRIEF_SYSTEM_PROMPT)

    async def _node_notify(self, state: MeetingState) -> dict:
        """Notify Slack node wrapper."""
        return await notify_slack(state, self.slack)

    async def _node_human_review(self, state: MeetingState) -> dict:
        """Human review node - this is an interrupt point.

        The workflow pauses here until resume() is called after the
        meeting ends with optional notes.
        """
        return state

    async def _node_capture_notes(self, state: MeetingState) -> dict:
        """Capture notes node wrapper."""
        return await capture_notes(state)

    async def _node_suggest_followup(self, state: MeetingState) -> dict:
        """Suggest follow-up node wrapper."""
        return await suggest_followup(state, self.llm)

    async def _node_audit(self, state: MeetingState) -> dict:
        """Audit log node - records the final state.

        Actual audit logging is handled by the service layer.
        """
        step = {
            "node": "audit_log",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "action_taken": state.get("action_taken"),
                "total_steps": len(state.get("steps", [])),
                "brief_sent": state.get("brief_sent", False),
                "notes_captured": state.get("notes_captured", False),
            },
            "error": None,
        }
        return {
            "steps": state.get("steps", []) + [step],
        }

    # Routing functions

    def _route_after_brief(
        self, state: MeetingState
    ) -> Literal["notify", "error"]:
        """Route after brief generation based on status."""
        if state.get("error"):
            return "error"

        brief = state.get("brief")
        if not brief:
            return "error"

        # Always notify - even low confidence briefs go to Slack
        # The needs_human_review flag is set for UI indication
        return "notify"

    # Public API

    async def run(
        self, meeting_record: MeetingRecord, config_dict: Optional[dict] = None
    ) -> MeetingState:
        """Run the agent for a single meeting.

        Args:
            meeting_record: MeetingRecord to process
            config_dict: Optional user config as dict

        Returns:
            Final agent state after processing
        """
        # Create initial state
        initial_state: MeetingState = {
            "meeting_id": str(meeting_record.id),
            "user_id": str(meeting_record.user_id),
            "config": config_dict or self._config_to_dict(),
            "_meeting_record": meeting_record,  # Internal use
            "meeting": None,
            "participant_contexts": [],
            "brief": None,
            "brief_sent": False,
            "brief_sent_at": None,
            "needs_human_review": False,
            "slack_message_ts": None,
            "notes_captured": False,
            "notes_content": None,
            "follow_up_suggestions": [],
            "action_taken": None,
            "status": "pending",
            "error": None,
            "trace_id": str(uuid4()),
            "steps": [],
        }

        # Configure with meeting_id as thread_id for checkpointing
        config = {"configurable": {"thread_id": str(meeting_record.id)}}

        # Run the graph
        result = await self.graph.ainvoke(initial_state, config)
        return result

    async def resume(
        self,
        meeting_id: str,
        notes_content: Optional[str] = None,
    ) -> MeetingState:
        """Resume the workflow after meeting ends.

        Args:
            meeting_id: Meeting ID (used as thread_id)
            notes_content: Optional post-meeting notes

        Returns:
            Final agent state after resuming
        """
        config = {"configurable": {"thread_id": meeting_id}}

        # Update with notes
        update = {
            "notes_content": notes_content,
        }

        # Resume execution
        result = await self.graph.ainvoke(update, config)
        return result

    async def get_state(self, meeting_id: str) -> Optional[MeetingState]:
        """Get the current state for a meeting.

        Args:
            meeting_id: Meeting ID (used as thread_id)

        Returns:
            Current state or None if not found
        """
        config = {"configurable": {"thread_id": meeting_id}}
        state = await self.graph.aget_state(config)
        return state.values if state else None

    def _config_to_dict(self) -> Optional[dict]:
        """Convert user config to dict for state."""
        if not self.config:
            return None

        return {
            "is_enabled": self.config.is_enabled,
            "brief_minutes_before": self.config.brief_minutes_before,
            "only_external_meetings": self.config.only_external_meetings,
            "min_attendees": self.config.min_attendees,
            "escalation_threshold": float(self.config.escalation_threshold),
        }
