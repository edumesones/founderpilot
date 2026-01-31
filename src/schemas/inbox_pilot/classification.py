"""Classification and draft result schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class EmailData(BaseModel):
    """Parsed email data for agent processing."""

    message_id: str
    thread_id: str
    sender: str
    sender_name: Optional[str] = None
    subject: str
    body: str
    snippet: str
    received_at: str
    thread_messages: list[dict] = Field(default_factory=list)
    attachments: list[dict] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    """Result of email classification by LLM."""

    category: Literal["urgent", "important", "routine", "spam"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    suggested_action: Literal["escalate", "draft", "archive", "ignore"]


class DraftResult(BaseModel):
    """Result of draft generation by LLM."""

    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    tone: Literal["formal", "casual", "friendly", "professional"]


class AgentStep(BaseModel):
    """Record of a single step in the agent workflow."""

    node: str
    timestamp: str
    result: Optional[dict] = None
    error: Optional[str] = None


class InboxState(BaseModel):
    """Complete state for InboxPilot agent workflow."""

    # Input
    message_id: str
    user_id: str

    # Fetched data
    email: Optional[EmailData] = None

    # Classification
    classification: Optional[ClassificationResult] = None

    # Draft
    draft: Optional[DraftResult] = None

    # Human review
    needs_human_review: bool = False
    human_decision: Optional[Literal["approve", "reject", "edit", "archive"]] = None
    edited_content: Optional[str] = None

    # Execution
    action_taken: Optional[str] = None

    # Error handling
    error: Optional[str] = None

    # Audit
    trace_id: str
    steps: list[AgentStep] = Field(default_factory=list)
