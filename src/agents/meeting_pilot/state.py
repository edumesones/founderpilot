"""State definition for MeetingPilot agent."""

from datetime import datetime
from typing import Literal, Optional, TypedDict


class AttendeeData(TypedDict):
    """Attendee information from calendar event."""

    email: str
    name: Optional[str]
    response_status: Literal["needsAction", "accepted", "declined", "tentative"]
    is_organizer: bool
    is_self: bool


class MeetingData(TypedDict):
    """Meeting data from calendar."""

    meeting_id: str  # UUID as string
    calendar_event_id: str
    title: str
    description: Optional[str]
    start_time: str  # ISO format
    end_time: str  # ISO format
    location: Optional[str]
    hangout_link: Optional[str]
    attendees: list[AttendeeData]
    is_external: bool
    duration_minutes: int


class ParticipantContext(TypedDict):
    """Context gathered for a single participant."""

    email: str
    name: Optional[str]
    email_count: int
    recent_subjects: list[str]
    last_contact: Optional[str]  # ISO format
    is_first_contact: bool
    summary: Optional[str]


class BriefResult(TypedDict):
    """Result of brief generation."""

    content: str
    confidence: float
    participant_contexts: list[ParticipantContext]
    suggested_objectives: list[str]
    warnings: list[str]
    generated_at: str  # ISO format


class AgentStep(TypedDict):
    """Record of a single step in the agent workflow."""

    node: str
    timestamp: str
    result: Optional[dict]
    error: Optional[str]


class MeetingState(TypedDict):
    """Complete state for MeetingPilot agent workflow.

    This is the main state object that flows through the LangGraph.

    The MeetingPilot workflow:
    1. Fetch meeting details from stored record
    2. Gather email context for each participant
    3. Generate meeting brief with LLM
    4. Send notification to Slack
    5. Wait for meeting to end (interrupt)
    6. Capture post-meeting notes
    7. Suggest follow-up actions
    8. Log everything to audit
    """

    # Input
    meeting_id: str  # UUID as string
    user_id: str  # UUID as string

    # User configuration (loaded at start)
    config: Optional[dict]

    # Meeting data (fetched from DB)
    meeting: Optional[MeetingData]

    # Context gathered
    participant_contexts: list[ParticipantContext]

    # Brief
    brief: Optional[BriefResult]
    brief_sent: bool
    brief_sent_at: Optional[str]  # ISO format

    # Human interaction
    needs_human_review: bool
    slack_message_ts: Optional[str]  # For updating message

    # Post-meeting
    notes_captured: bool
    notes_content: Optional[str]
    follow_up_suggestions: list[str]

    # Execution status
    action_taken: Optional[str]
    status: Literal[
        "pending",
        "gathering_context",
        "generating_brief",
        "brief_sent",
        "waiting_for_meeting",
        "capturing_notes",
        "completed",
        "cancelled",
        "error",
    ]

    # Error handling
    error: Optional[str]

    # Audit
    trace_id: str
    steps: list[AgentStep]


# Default initial state factory
def create_initial_state(
    meeting_id: str,
    user_id: str,
    config: Optional[dict] = None,
    trace_id: Optional[str] = None,
) -> MeetingState:
    """Create initial state for a new meeting processing run.

    Args:
        meeting_id: UUID of the meeting record
        user_id: UUID of the user
        config: Optional user configuration dict
        trace_id: Optional trace ID (generated if not provided)

    Returns:
        Initial MeetingState
    """
    from uuid import uuid4

    return MeetingState(
        meeting_id=meeting_id,
        user_id=user_id,
        config=config,
        meeting=None,
        participant_contexts=[],
        brief=None,
        brief_sent=False,
        brief_sent_at=None,
        needs_human_review=False,
        slack_message_ts=None,
        notes_captured=False,
        notes_content=None,
        follow_up_suggestions=[],
        action_taken=None,
        status="pending",
        error=None,
        trace_id=trace_id or str(uuid4()),
        steps=[],
    )
