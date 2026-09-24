# FEAT-003: InboxPilot - Technical Design

## Overview

InboxPilot es un agente LangGraph que procesa emails de Gmail en tiempo real. Usa un StateGraph con nodos para fetch, classify, draft, y escalate. Implementa human-in-the-loop via Slack actions y persiste estado en PostgreSQL para resiliencia.

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  GMAIL                                           │
│   ┌────────────────┐                                                            │
│   │  Gmail Inbox   │◀─────────────────────────────────────────────┐             │
│   └───────┬────────┘                                              │             │
│           │ Push Notification (Pub/Sub)                           │ Send        │
│           ▼                                                       │             │
└───────────┼───────────────────────────────────────────────────────┼─────────────┘
            │                                                       │
            ▼                                                       │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FOUNDERPILOT API                                    │
│                                                                                  │
│   ┌────────────────┐      ┌────────────────┐      ┌────────────────┐           │
│   │   /webhooks/   │      │    Celery      │      │   InboxPilot   │           │
│   │    gmail       │─────▶│    Queue       │─────▶│    Agent       │───────────┤
│   │                │      │   (Redis)      │      │  (LangGraph)   │           │
│   └────────────────┘      └────────────────┘      └───────┬────────┘           │
│                                                           │                     │
│                           ┌───────────────────────────────┼─────────────────┐   │
│                           │                               │                 │   │
│                           ▼                               ▼                 ▼   │
│                   ┌──────────────┐             ┌──────────────┐    ┌──────────┐│
│                   │  PostgreSQL  │             │    Slack     │    │ Langfuse ││
│                   │  Checkpointer│             │  Notifier    │    │  Tracer  ││
│                   │  + Audit Log │             │              │    │          ││
│                   └──────────────┘             └──────────────┘    └──────────┘│
│                                                       │                         │
└───────────────────────────────────────────────────────┼─────────────────────────┘
                                                        │
                                                        ▼
                                               ┌────────────────┐
                                               │     SLACK      │
                                               │  Notification  │
                                               │  + Actions     │
                                               └────────────────┘
```

### Agent State Machine (LangGraph)

```
                    ┌─────────────────┐
                    │   START         │
                    │  (new email)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  fetch_email    │  ◀──── Gmail API: get full message + thread
                    │                 │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  classify       │  ◀──── LLM: GPT-4o-mini
                    │                 │        Output: category + confidence
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
         ┌────────┐    ┌──────────┐   ┌──────────┐
         │ urgent │    │ routine  │   │  spam    │
         │        │    │          │   │          │
         └───┬────┘    └────┬─────┘   └────┬─────┘
             │              │              │
             │              ▼              │
             │     ┌─────────────────┐     │
             │     │ draft_response  │     │
             │     │                 │     │
             │     └────────┬────────┘     │
             │              │              │
             │    ┌─────────┴─────────┐    │
             │    │ confidence < 80%? │    │
             │    └────┬─────────┬────┘    │
             │         │ yes     │ no      │
             │         ▼         ▼         │
             │  ┌──────────┐  ┌──────────┐ │
             └─▶│ escalate │  │auto_send │◀┘
                │ (Slack)  │  │          │
                └────┬─────┘  └────┬─────┘
                     │             │
                     ▼             │
              ┌──────────────┐     │
              │ human_review │     │  (interrupt point - waits for Slack action)
              │              │     │
              └──────┬───────┘     │
                     │             │
        ┌────────────┼────────────┐│
        │            │            ││
        ▼            ▼            ▼▼
   ┌────────┐  ┌──────────┐  ┌──────────┐
   │approve │  │  edit    │  │ reject/  │
   │        │  │          │  │ archive  │
   └───┬────┘  └────┬─────┘  └────┬─────┘
       │            │             │
       └────────────┼─────────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ execute_action  │  ◀──── Gmail API: send/archive/label
           │                 │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │  audit_log      │  ◀──── PostgreSQL: record action
           │                 │
           └────────┬────────┘
                    │
                    ▼
                  [END]
```

---

## File Structure

### New Files to Create

```
src/
├── agents/
│   └── inbox_pilot/
│       ├── __init__.py
│       ├── agent.py              # Main InboxPilotAgent class
│       ├── state.py              # InboxState TypedDict
│       ├── nodes/
│       │   ├── __init__.py
│       │   ├── fetch.py          # fetch_email node
│       │   ├── classify.py       # classify node
│       │   ├── draft.py          # draft_response node
│       │   ├── escalate.py       # escalate node
│       │   └── execute.py        # execute_action node
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── classify.py       # Classification prompt
│       │   └── draft.py          # Draft generation prompt
│       └── config.py             # Agent configuration
│
├── integrations/
│   └── gmail/
│       ├── __init__.py
│       ├── client.py             # Gmail API wrapper
│       ├── webhook.py            # Pub/Sub webhook handler
│       ├── labels.py             # Label management
│       └── schemas.py            # Email schemas
│
├── api/
│   └── routes/
│       └── webhooks/
│           └── gmail.py          # POST /webhooks/gmail
│
├── workers/
│   └── tasks/
│       └── inbox_pilot.py        # Celery task: process_email
│
├── models/
│   └── inbox_pilot/
│       ├── __init__.py
│       ├── email_record.py       # Processed email tracking
│       └── agent_config.py       # Per-user agent config
│
├── schemas/
│   └── inbox_pilot/
│       ├── __init__.py
│       ├── email.py              # Email DTOs
│       ├── classification.py     # Classification result
│       └── config.py             # Agent config schemas
│
└── services/
    └── inbox_pilot/
        ├── __init__.py
        └── service.py            # InboxPilotService

tests/
├── unit/
│   └── agents/
│       └── inbox_pilot/
│           ├── test_classify.py
│           ├── test_draft.py
│           └── test_state.py
├── integration/
│   └── test_inbox_pilot_agent.py
└── fixtures/
    └── emails/
        ├── urgent_email.json
        ├── routine_email.json
        └── spam_email.json
```

### Files to Modify

| File | Changes |
|------|---------|
| `src/api/main.py` | Add gmail webhook router |
| `src/workers/celery_app.py` | Register inbox_pilot tasks |
| `alembic/versions/` | Add email_records, inbox_config tables |

---

## Data Model

### Entities

```python
# src/models/inbox_pilot/email_record.py
class EmailRecord(Base):
    """Tracks processed emails for idempotency and audit."""
    __tablename__ = "email_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    gmail_message_id: Mapped[str] = mapped_column(String(255), unique=True)  # Idempotency
    thread_id: Mapped[str] = mapped_column(String(255), index=True)

    # Email metadata
    sender: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(500))
    snippet: Mapped[str] = mapped_column(String(500))  # First 500 chars
    received_at: Mapped[datetime]

    # Classification
    category: Mapped[str] = mapped_column(String(50))  # urgent|important|routine|spam
    confidence: Mapped[float]

    # Processing
    status: Mapped[str] = mapped_column(String(50))  # pending|processing|escalated|completed
    draft_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_taken: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # sent|archived|rejected

    # Timestamps
    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Audit
    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("workflow_runs.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


# src/models/inbox_pilot/agent_config.py
class InboxPilotConfig(Base):
    """Per-user InboxPilot configuration."""
    __tablename__ = "inbox_pilot_configs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)

    # Thresholds
    escalation_threshold: Mapped[float] = mapped_column(default=0.8)
    draft_threshold: Mapped[float] = mapped_column(default=0.7)

    # Preferences
    auto_archive_spam: Mapped[bool] = mapped_column(default=True)
    draft_for_routine: Mapped[bool] = mapped_column(default=True)
    escalate_urgent: Mapped[bool] = mapped_column(default=True)

    # VIP contacts (always escalate)
    vip_domains: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    vip_emails: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])

    # Ignore patterns
    ignore_senders: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])

    # Active status
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Database Schema

```sql
-- Migration: create_inbox_pilot_tables

CREATE TABLE email_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gmail_message_id VARCHAR(255) UNIQUE NOT NULL,
    thread_id VARCHAR(255) NOT NULL,

    sender VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    snippet VARCHAR(500),
    received_at TIMESTAMP NOT NULL,

    category VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,

    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    draft_content TEXT,
    action_taken VARCHAR(50),

    processed_at TIMESTAMP,
    completed_at TIMESTAMP,
    workflow_run_id UUID REFERENCES workflow_runs(id),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_email_records_user_id ON email_records(user_id);
CREATE INDEX idx_email_records_thread_id ON email_records(thread_id);
CREATE INDEX idx_email_records_status ON email_records(status);
CREATE INDEX idx_email_records_received_at ON email_records(received_at);

CREATE TABLE inbox_pilot_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    escalation_threshold FLOAT DEFAULT 0.8,
    draft_threshold FLOAT DEFAULT 0.7,

    auto_archive_spam BOOLEAN DEFAULT TRUE,
    draft_for_routine BOOLEAN DEFAULT TRUE,
    escalate_urgent BOOLEAN DEFAULT TRUE,

    vip_domains TEXT[] DEFAULT '{}',
    vip_emails TEXT[] DEFAULT '{}',
    ignore_senders TEXT[] DEFAULT '{}',

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Design

### Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/webhooks/gmail` | Gmail push notification | Pub/Sub signature |
| GET | `/api/v1/inbox-pilot/config` | Get user's config | JWT |
| PUT | `/api/v1/inbox-pilot/config` | Update config | JWT |
| GET | `/api/v1/inbox-pilot/emails` | List processed emails | JWT |
| GET | `/api/v1/inbox-pilot/emails/{id}` | Get email details | JWT |
| POST | `/api/v1/inbox-pilot/emails/{id}/action` | Manual action (approve/reject) | JWT |
| POST | `/api/v1/inbox-pilot/watch` | Setup Gmail watch | JWT |
| DELETE | `/api/v1/inbox-pilot/watch` | Stop Gmail watch | JWT |

### Request/Response Examples

```json
// POST /webhooks/gmail (from Google Pub/Sub)
{
  "message": {
    "data": "base64-encoded-notification",
    "messageId": "123",
    "publishTime": "2026-01-31T10:00:00Z"
  },
  "subscription": "projects/xxx/subscriptions/gmail-push"
}
// Response: 200 OK (must respond quickly)

// GET /api/v1/inbox-pilot/config
// Response 200
{
  "escalation_threshold": 0.8,
  "draft_threshold": 0.7,
  "auto_archive_spam": true,
  "draft_for_routine": true,
  "escalate_urgent": true,
  "vip_domains": ["importantclient.com"],
  "vip_emails": ["ceo@bigcorp.com"],
  "ignore_senders": ["noreply@newsletter.com"],
  "is_active": true
}

// GET /api/v1/inbox-pilot/emails?status=escalated&limit=10
// Response 200
{
  "items": [
    {
      "id": "uuid",
      "gmail_message_id": "msg123",
      "sender": "john@company.com",
      "subject": "Urgent: Contract review needed",
      "category": "urgent",
      "confidence": 0.95,
      "status": "escalated",
      "received_at": "2026-01-31T09:00:00Z",
      "draft_content": null
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 10
}

// POST /api/v1/inbox-pilot/emails/{id}/action
// Request
{
  "action": "approve",
  "edited_content": null  // Optional: if user edited the draft
}
// Response 200
{
  "success": true,
  "action_taken": "sent"
}
```

---

## Service Layer

### InboxPilotService

```python
# src/services/inbox_pilot/service.py
class InboxPilotService:
    """Business logic for InboxPilot operations."""

    def __init__(
        self,
        db: AsyncSession,
        gmail_client: GmailClient,
        slack_notifier: SlackNotifier,
        llm_router: LLMRouter,
    ):
        self.db = db
        self.gmail = gmail_client
        self.slack = slack_notifier
        self.llm = llm_router

    async def process_email(
        self,
        user_id: UUID,
        message_id: str
    ) -> EmailRecord:
        """Main entry point for processing a new email."""
        # Check idempotency
        existing = await self.get_email_by_message_id(message_id)
        if existing:
            return existing

        # Get user config
        config = await self.get_config(user_id)

        # Create agent and run
        agent = InboxPilotAgent(
            gmail=self.gmail,
            slack=self.slack,
            llm=self.llm,
            config=config,
        )

        result = await agent.run(message_id)

        # Save record
        record = EmailRecord(
            user_id=user_id,
            gmail_message_id=message_id,
            **result.dict()
        )
        self.db.add(record)
        await self.db.commit()

        return record

    async def handle_slack_action(
        self,
        user_id: UUID,
        email_id: UUID,
        action: str,
        payload: dict,
    ) -> EmailRecord:
        """Handle Slack action button callback."""
        record = await self.get_email(email_id)

        if action == "approve":
            await self.gmail.send_draft(record.draft_content)
            record.action_taken = "sent"
        elif action == "reject":
            record.action_taken = "rejected"
        elif action == "edit":
            # User edited the draft
            record.draft_content = payload.get("edited_content")
            await self.gmail.send_draft(record.draft_content)
            record.action_taken = "sent"
        elif action == "archive":
            await self.gmail.archive(record.gmail_message_id)
            record.action_taken = "archived"

        record.status = "completed"
        record.completed_at = datetime.utcnow()
        await self.db.commit()

        return record

    async def get_config(self, user_id: UUID) -> InboxPilotConfig:
        """Get or create default config for user."""
        pass

    async def update_config(
        self,
        user_id: UUID,
        updates: InboxPilotConfigUpdate
    ) -> InboxPilotConfig:
        """Update user's config."""
        pass

    async def setup_watch(self, user_id: UUID) -> dict:
        """Setup Gmail push notifications for user."""
        pass

    async def stop_watch(self, user_id: UUID) -> None:
        """Stop Gmail push notifications."""
        pass
```

---

## Agent Implementation

### State Definition

```python
# src/agents/inbox_pilot/state.py
from typing import TypedDict, Optional, Literal

class EmailData(TypedDict):
    message_id: str
    thread_id: str
    sender: str
    sender_name: Optional[str]
    subject: str
    body: str
    snippet: str
    received_at: str
    thread_messages: list[dict]  # Previous messages in thread
    attachments: list[dict]  # Metadata only

class ClassificationResult(TypedDict):
    category: Literal["urgent", "important", "routine", "spam"]
    confidence: float
    reasoning: str
    suggested_action: Literal["escalate", "draft", "archive", "ignore"]

class DraftResult(TypedDict):
    content: str
    confidence: float
    tone: str

class InboxState(TypedDict):
    """State for InboxPilot agent graph."""
    # Input
    message_id: str
    user_id: str

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
    steps: list[dict]  # Audit trail of all steps
```

### Agent Class

```python
# src/agents/inbox_pilot/agent.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

class InboxPilotAgent:
    """LangGraph agent for email triage."""

    def __init__(
        self,
        gmail: GmailClient,
        slack: SlackNotifier,
        llm: LLMRouter,
        config: InboxPilotConfig,
        checkpointer: PostgresSaver,
    ):
        self.gmail = gmail
        self.slack = slack
        self.llm = llm
        self.config = config
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledGraph:
        graph = StateGraph(InboxState)

        # Add nodes
        graph.add_node("fetch_email", self._fetch_email)
        graph.add_node("classify", self._classify)
        graph.add_node("draft_response", self._draft_response)
        graph.add_node("escalate", self._escalate)
        graph.add_node("human_review", self._human_review)
        graph.add_node("execute_action", self._execute_action)
        graph.add_node("audit_log", self._audit_log)

        # Define edges
        graph.set_entry_point("fetch_email")

        graph.add_edge("fetch_email", "classify")

        graph.add_conditional_edges(
            "classify",
            self._route_after_classify,
            {
                "draft": "draft_response",
                "escalate": "escalate",
                "archive": "execute_action",
            }
        )

        graph.add_conditional_edges(
            "draft_response",
            self._route_after_draft,
            {
                "escalate": "escalate",
                "auto_send": "execute_action",
            }
        )

        graph.add_edge("escalate", "human_review")

        graph.add_edge("human_review", "execute_action")

        graph.add_edge("execute_action", "audit_log")

        graph.add_edge("audit_log", END)

        return graph.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["human_review"],  # Pause for human input
        )

    async def run(self, message_id: str) -> InboxState:
        """Run the agent for a single email."""
        initial_state: InboxState = {
            "message_id": message_id,
            "user_id": str(self.config.user_id),
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

        config = {"configurable": {"thread_id": message_id}}

        result = await self.graph.ainvoke(initial_state, config)
        return result

    async def resume(self, message_id: str, human_input: dict) -> InboxState:
        """Resume after human review."""
        config = {"configurable": {"thread_id": message_id}}

        # Update state with human decision
        update = {
            "human_decision": human_input["action"],
            "edited_content": human_input.get("edited_content"),
        }

        result = await self.graph.ainvoke(update, config)
        return result

    # Node implementations
    async def _fetch_email(self, state: InboxState) -> dict:
        """Fetch full email data from Gmail."""
        email_data = await self.gmail.get_message(
            state["message_id"],
            include_thread=True,
            thread_limit=5,
        )
        return {
            "email": email_data,
            "steps": state["steps"] + [{"node": "fetch_email", "timestamp": datetime.utcnow().isoformat()}],
        }

    async def _classify(self, state: InboxState) -> dict:
        """Classify email using LLM."""
        prompt = build_classification_prompt(state["email"])

        result = await self.llm.call(
            task_type="classify",
            prompt=prompt,
            response_model=ClassificationResult,
        )

        return {
            "classification": result,
            "steps": state["steps"] + [{"node": "classify", "result": result, "timestamp": datetime.utcnow().isoformat()}],
        }

    async def _draft_response(self, state: InboxState) -> dict:
        """Generate draft response using LLM."""
        prompt = build_draft_prompt(state["email"], state["classification"])

        result = await self.llm.call(
            task_type="generate",
            prompt=prompt,
            response_model=DraftResult,
        )

        return {
            "draft": result,
            "steps": state["steps"] + [{"node": "draft_response", "result": result, "timestamp": datetime.utcnow().isoformat()}],
        }

    async def _escalate(self, state: InboxState) -> dict:
        """Send Slack notification for human review."""
        await self.slack.send_email_notification(
            user_id=state["user_id"],
            email=state["email"],
            classification=state["classification"],
            draft=state.get("draft"),
        )

        return {
            "needs_human_review": True,
            "steps": state["steps"] + [{"node": "escalate", "timestamp": datetime.utcnow().isoformat()}],
        }

    async def _human_review(self, state: InboxState) -> dict:
        """Wait for human decision (interrupt point)."""
        # This node is an interrupt point
        # State will be updated externally via resume()
        return state

    async def _execute_action(self, state: InboxState) -> dict:
        """Execute the decided action on Gmail."""
        action = state.get("human_decision") or self._determine_auto_action(state)

        if action == "approve" or action == "auto_send":
            content = state.get("edited_content") or state["draft"]["content"]
            await self.gmail.send_reply(state["email"]["message_id"], content)
            action_taken = "sent"
        elif action == "archive":
            await self.gmail.archive(state["email"]["message_id"])
            action_taken = "archived"
        elif action == "reject":
            action_taken = "rejected"
        else:
            action_taken = "ignored"

        # Add label
        label = f"FP_{state['classification']['category'].title()}"
        await self.gmail.add_label(state["email"]["message_id"], label)

        return {
            "action_taken": action_taken,
            "steps": state["steps"] + [{"node": "execute_action", "action": action_taken, "timestamp": datetime.utcnow().isoformat()}],
        }

    async def _audit_log(self, state: InboxState) -> dict:
        """Record audit entry."""
        # Audit is handled by the service layer
        return state

    # Routing functions
    def _route_after_classify(self, state: InboxState) -> str:
        classification = state["classification"]

        # Check VIP - always escalate
        sender_domain = state["email"]["sender"].split("@")[-1]
        if sender_domain in self.config.vip_domains:
            return "escalate"
        if state["email"]["sender"] in self.config.vip_emails:
            return "escalate"

        # Route by category
        if classification["category"] == "urgent":
            return "escalate"
        elif classification["category"] == "spam":
            return "archive" if self.config.auto_archive_spam else "escalate"
        elif classification["category"] == "routine":
            if self.config.draft_for_routine:
                return "draft"
            return "archive"
        else:  # important
            return "escalate"

    def _route_after_draft(self, state: InboxState) -> str:
        draft = state["draft"]

        if draft["confidence"] < self.config.escalation_threshold:
            return "escalate"

        # Auto-send only if high confidence and routine
        if draft["confidence"] >= 0.9 and state["classification"]["category"] == "routine":
            return "auto_send"

        return "escalate"

    def _determine_auto_action(self, state: InboxState) -> str:
        """Determine action when no human review needed."""
        if state["classification"]["category"] == "spam":
            return "archive"
        if state.get("draft"):
            return "auto_send"
        return "archive"
```

---

## Prompts

### Classification Prompt

```python
# src/agents/inbox_pilot/prompts/classify.py
CLASSIFICATION_SYSTEM_PROMPT = """You are an email classification assistant for busy founders.

Your job is to classify incoming emails into one of four categories:
- URGENT: Requires immediate attention (deadlines, emergencies, important client issues)
- IMPORTANT: Needs attention but not immediate (business inquiries, partnership offers, team matters)
- ROUTINE: Standard emails that can be handled with templates (meeting scheduling, confirmations, FYIs)
- SPAM: Promotional, newsletter, or irrelevant content

Consider:
1. Sender relationship (client, partner, team, unknown)
2. Subject line urgency indicators
3. Content importance to business
4. Time sensitivity mentioned
5. Thread context (is this part of ongoing conversation?)

Respond with JSON:
{
  "category": "urgent|important|routine|spam",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation",
  "suggested_action": "escalate|draft|archive|ignore"
}
"""

def build_classification_prompt(email: EmailData) -> str:
    thread_context = ""
    if email.get("thread_messages"):
        thread_context = "\n\nPrevious messages in thread:\n"
        for msg in email["thread_messages"][-3:]:
            thread_context += f"- From: {msg['sender']}, Subject: {msg['subject']}\n"

    return f"""Classify this email:

From: {email['sender']} ({email.get('sender_name', 'Unknown')})
Subject: {email['subject']}
Received: {email['received_at']}

Body:
{email['body'][:2000]}

{thread_context}

Attachments: {len(email.get('attachments', []))} files
"""
```

### Draft Prompt

```python
# src/agents/inbox_pilot/prompts/draft.py
DRAFT_SYSTEM_PROMPT = """You are an email drafting assistant for a busy founder.

Your job is to draft professional, concise responses to routine emails.

Guidelines:
1. Match the tone of the original email
2. Be direct and action-oriented
3. Keep responses brief (2-4 sentences for simple matters)
4. Include clear next steps when applicable
5. Sign off appropriately based on relationship

Do NOT draft responses for:
- Complex negotiations
- Sensitive topics
- Anything requiring creative input
- Legal or financial matters

Respond with JSON:
{
  "content": "The draft email response",
  "confidence": 0.0-1.0,
  "tone": "formal|casual|friendly|professional"
}
"""

def build_draft_prompt(email: EmailData, classification: ClassificationResult) -> str:
    return f"""Draft a response to this email:

Classification: {classification['category']} (confidence: {classification['confidence']})
Reasoning: {classification['reasoning']}

Original Email:
From: {email['sender']}
Subject: {email['subject']}

{email['body'][:3000]}

Draft a brief, professional response.
"""
```

---

## Dependencies

### New Packages

| Package | Version | Purpose |
|---------|---------|---------|
| google-api-python-client | ^2.100.0 | Gmail API |
| google-auth-oauthlib | ^1.0.0 | OAuth flow |
| langgraph | ^0.0.40 | Agent framework |
| langgraph-checkpoint-postgres | ^0.0.5 | State persistence |

### External Services

| Service | Purpose | Config Needed |
|---------|---------|---------------|
| Gmail API | Email access | OAuth credentials, Pub/Sub topic |
| Google Pub/Sub | Push notifications | Topic, subscription |
| Slack API | Notifications | Bot token (from FEAT-006) |

---

## Error Handling

| Error | HTTP Code | Response |
|-------|-----------|----------|
| Email not found | 404 | `{"error": "Email not found"}` |
| Gmail token expired | 401 | `{"error": "Gmail authorization required", "action": "reauth"}` |
| Rate limit exceeded | 429 | `{"error": "Too many requests", "retry_after": 60}` |
| LLM error | 500 | `{"error": "Processing failed", "fallback": "escalated"}` |
| Invalid config | 422 | `{"error": "Invalid configuration", "details": [...]}` |

---

## Security Considerations

- [x] Gmail tokens encrypted with Fernet (AES-128)
- [x] Refresh tokens stored in AWS Secrets Manager
- [x] Email body NOT stored in audit log (only snippet)
- [x] Rate limiting: 50 emails/hour per user (trial), 500/hour (paid)
- [x] Webhook signature validation for Pub/Sub
- [x] tenant_id isolation on all queries

---

## Performance Considerations

| Aspect | Approach |
|--------|----------|
| Caching | Redis cache for user configs (5 min TTL) |
| Pagination | Cursor-based for email list |
| Async | All Gmail/LLM calls are async |
| Batching | Individual processing, batch for digest mode |
| Indexing | gmail_message_id unique, user_id+status composite |

---

## Testing Strategy

| Type | Coverage Target | Tools |
|------|-----------------|-------|
| Unit | 80%+ | pytest, pytest-asyncio |
| Integration | Main flows | pytest, testcontainers |
| E2E | Critical paths | pytest, mocked Gmail |

### Test Scenarios

1. **Happy path**: Email → Classify → Draft → Approve → Send
2. **Escalation**: Low confidence → Slack notification → Human approve
3. **Spam**: Detected as spam → Auto-archive
4. **VIP**: From VIP domain → Always escalate
5. **Error recovery**: Gmail rate limit → Retry with backoff
6. **Idempotency**: Same email twice → Only processed once

---

## Implementation Order

1. **Phase 1: Foundation** (Day 1-2)
   - Create file structure
   - Create database models + migration
   - Create Pydantic schemas

2. **Phase 2: Gmail Integration** (Day 2-3)
   - Gmail client wrapper
   - OAuth token management
   - Push notification webhook

3. **Phase 3: Agent Core** (Day 3-5)
   - State definition
   - LangGraph agent structure
   - Classification node + prompt
   - Draft node + prompt

4. **Phase 4: Escalation** (Day 5-6)
   - Slack notification (depends on FEAT-006)
   - Human review interrupt
   - Resume flow

5. **Phase 5: API & Service** (Day 6-7)
   - Service layer
   - API endpoints
   - Celery task

6. **Phase 6: Testing** (Day 7-8)
   - Unit tests
   - Integration tests
   - E2E test

7. **Phase 7: Polish** (Day 8)
   - Error handling
   - Logging
   - Documentation

---

## Open Technical Questions

- [x] LangGraph checkpointer setup? -> PostgresSaver with connection pool
- [x] Gmail watch expiration? -> 7 days, renew via cron

---

## References

- [Gmail API Push Notifications](https://developers.google.com/gmail/api/guides/push)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/persistence/)

---

*Created: 2026-01-31*
*Last updated: 2026-01-31*
*Approved: [x] Ready for implementation*
