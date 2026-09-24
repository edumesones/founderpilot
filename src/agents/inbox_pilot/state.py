"""State definition for InboxPilot agent."""

from typing import Literal, Optional, TypedDict


class EmailData(TypedDict):
    """Parsed email data from Gmail."""

    message_id: str
    thread_id: str
    sender: str
    sender_name: Optional[str]
    subject: str
    body: str
    snippet: str
    received_at: str
    thread_messages: list[dict]
    attachments: list[dict]
    labels: list[str]


class ClassificationResult(TypedDict):
    """Result of email classification."""

    category: Literal["urgent", "important", "routine", "spam"]
    confidence: float
    reasoning: str
    suggested_action: Literal["escalate", "draft", "archive", "ignore"]


class DraftResult(TypedDict):
    """Result of draft generation."""

    content: str
    confidence: float
    tone: Literal["formal", "casual", "friendly", "professional"]


class AgentStep(TypedDict):
    """Record of a single step in the agent workflow."""

    node: str
    timestamp: str
    result: Optional[dict]
    error: Optional[str]


class InboxState(TypedDict):
    """Complete state for InboxPilot agent workflow.

    This is the main state object that flows through the LangGraph.
    """

    # Input
    message_id: str
    user_id: str

    # User configuration (loaded at start)
    config: Optional[dict]

    # Fetched data
    email: Optional[EmailData]

    # Classification
    classification: Optional[ClassificationResult]

    # Draft
    draft: Optional[DraftResult]

    # Human review
    needs_human_review: bool
    human_decision: Optional[Literal["approve", "reject", "edit", "archive"]]
    edited_content: Optional[str]

    # Execution
    action_taken: Optional[str]

    # Error handling
    error: Optional[str]

    # Audit
    trace_id: str
    steps: list[AgentStep]
