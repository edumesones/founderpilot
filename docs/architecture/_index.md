# FounderPilot - Architecture Overview

## System Context

```
                                    ┌─────────────────────────────────────────────────────────────┐
                                    │                         EXTERNAL                            │
                                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐    │
                                    │  │  Gmail  │  │  Slack  │  │ Calendar│  │   Stripe    │    │
                                    │  │   API   │  │   API   │  │   API   │  │    API      │    │
                                    │  └────┬────┘  └────┬────┘  └────┬────┘  └──────┬──────┘    │
                                    └───────┼───────────┼───────────┼──────────────┼────────────┘
                                            │           │           │              │
                                            ▼           ▼           ▼              ▼
┌───────────────────┐              ┌────────────────────────────────────────────────────────────┐
│                   │              │                      FOUNDERPILOT                          │
│    Founder        │              │                                                            │
│    (Browser)      │──────────────▶  ┌──────────────┐      ┌──────────────────────────────┐   │
│                   │              │  │   Next.js    │      │         FastAPI              │   │
│   Dashboard       │              │  │   Frontend   │─────▶│          API                 │   │
│                   │              │  │   (Vercel)   │      │                              │   │
└───────────────────┘              │  └──────────────┘      └──────────────┬───────────────┘   │
                                   │                                        │                   │
┌───────────────────┐              │                                        ▼                   │
│                   │              │  ┌──────────────┐      ┌──────────────────────────────┐   │
│    Founder        │              │  │    Slack     │      │        LangGraph             │   │
│    (Slack)        │──────────────▶  │     Bot      │─────▶│        Agents                │   │
│                   │              │  │   (Bolt)     │      │                              │   │
│   Notifications   │              │  └──────────────┘      │  ┌───────────┐┌───────────┐  │   │
│   Quick Actions   │              │                        │  │InboxPilot ││InvoicePilot│ │   │
└───────────────────┘              │                        │  │  (Email)  ││  (Cobros)  │ │   │
                                   │                        │  └───────────┘└───────────┘  │   │
                                   │                        │       ┌───────────────┐      │   │
                                   │                        │       │ MeetingPilot  │      │   │
                                   │                        │       │  (Calendar)   │      │   │
                                   │                        │       └───────────────┘      │   │
                                   │                        └──────────────┬───────────────┘   │
                                   │                                       │                   │
                                   │          ┌────────────────────────────┼───────────────┐   │
                                   │          │                            │               │   │
                                   │          ▼                            ▼               ▼   │
                                   │  ┌──────────────┐      ┌─────────────────┐  ┌─────────┐   │
                                   │  │    Redis     │      │   PostgreSQL    │  │ Langfuse│   │
                                   │  │  (Queue +    │      │   (Data +       │  │ (Traces)│   │
                                   │  │   Cache)     │      │   Audit Logs)   │  │         │   │
                                   │  └──────────────┘      └─────────────────┘  └─────────┘   │
                                   │                                                            │
                                   │  ┌──────────────┐      ┌─────────────────────────────┐    │
                                   │  │   Celery     │      │          LLM Providers      │    │
                                   │  │   Workers    │─────▶│  ┌─────────┐  ┌──────────┐  │    │
                                   │  │   + Beat     │      │  │ Claude  │  │  GPT-4o  │  │    │
                                   │  └──────────────┘      │  └─────────┘  └──────────┘  │    │
                                   │                        └─────────────────────────────┘    │
                                   └────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | ADR |
|-------|------------|-----|
| Agent Framework | Python 3.11 + LangGraph | [ADR-001](../decisions/ADR-001-python-langgraph.md) |
| Backend API | FastAPI + Pydantic | [ADR-002](../decisions/ADR-002-fastapi.md) |
| Database | PostgreSQL 15 | [ADR-003](../decisions/ADR-003-postgresql.md) |
| Queue/Cache | Redis + Celery | [ADR-004](../decisions/ADR-004-redis-celery.md) |
| Auth | JWT + OAuth2 (Google) | [ADR-005](../decisions/ADR-005-jwt-oauth2.md) |
| Frontend | Next.js 14 + Slack Bot | [ADR-006](../decisions/ADR-006-nextjs-slack.md) |
| LLM | Claude + GPT-4o (multi-provider) | [ADR-007](../decisions/ADR-007-llm-providers.md) |
| Observability | Langfuse + CloudWatch | [ADR-008](../decisions/ADR-008-observability.md) |
| Deployment | Docker + AWS ECS Fargate | [ADR-009](../decisions/ADR-009-docker-ecs.md) |

## Project Structure

```
founderpilot/
├── docker-compose.yml          # Local development
├── Dockerfile.api              # API container
├── Dockerfile.worker           # Celery worker container
│
├── src/
│   ├── api/                    # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py             # App entrypoint
│   │   ├── routes/
│   │   │   ├── auth.py         # OAuth2 endpoints
│   │   │   ├── agents.py       # Agent config endpoints
│   │   │   ├── workflows.py    # Workflow triggers
│   │   │   └── webhooks.py     # Gmail, Slack webhooks
│   │   ├── dependencies.py     # FastAPI deps
│   │   └── middleware.py       # Auth, logging
│   │
│   ├── agents/                 # LangGraph agents
│   │   ├── __init__.py
│   │   ├── base.py             # Base agent class
│   │   ├── inbox_pilot.py      # InboxPilot - Email triage & drafts
│   │   ├── invoice_pilot.py    # InvoicePilot - Invoice tracking
│   │   └── meeting_pilot.py    # MeetingPilot - Meeting prep
│   │
│   ├── integrations/           # External APIs
│   │   ├── gmail.py
│   │   ├── slack.py
│   │   ├── calendar.py
│   │   └── stripe.py
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── agent_config.py
│   │   ├── workflow_run.py
│   │   └── audit_log.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py
│   │   ├── agent.py
│   │   └── workflow.py
│   │
│   ├── services/               # Business logic
│   │   ├── auth.py
│   │   ├── agent_runner.py
│   │   └── audit.py
│   │
│   ├── workers/                # Celery tasks
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── tasks.py
│   │   └── beat_schedule.py
│   │
│   └── core/                   # Shared utilities
│       ├── config.py           # Settings (pydantic-settings)
│       ├── database.py         # DB connection
│       ├── llm.py              # LLM provider abstraction
│       └── logging.py          # Structured logging
│
├── frontend/                   # Next.js app (separate repo optional)
│   ├── app/
│   ├── components/
│   └── lib/
│
├── slack_bot/                  # Slack Bolt app
│   ├── __init__.py
│   ├── app.py
│   └── handlers/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── alembic/                    # DB migrations
│   ├── versions/
│   └── env.py
│
└── docs/
    ├── architecture/
    ├── decisions/
    └── features/
```

## Key Patterns

### 1. Agent Architecture (LangGraph)

```python
# Cada agente es un StateGraph con nodos auditables
class InboxPilotAgent:
    def build_graph(self):
        graph = StateGraph(InboxState)

        graph.add_node("fetch_emails", self.fetch_emails)
        graph.add_node("classify", self.classify_email)
        graph.add_node("draft_response", self.draft_response)
        graph.add_node("human_review", self.human_review)  # Interrupt point
        graph.add_node("send_or_archive", self.send_or_archive)

        # Edges with conditions
        graph.add_conditional_edges(
            "classify",
            self.should_draft_or_archive,
            {"draft": "draft_response", "archive": "send_or_archive"}
        )

        # Human-in-loop for important emails
        graph.add_conditional_edges(
            "draft_response",
            self.needs_human_review,
            {"yes": "human_review", "no": "send_or_archive"}
        )

        return graph.compile(checkpointer=PostgresCheckpointer())
```

### 2. Audit Trail

```python
# Cada acción del agente se registra
@dataclass
class AuditEntry:
    id: UUID
    timestamp: datetime
    workflow_id: UUID
    agent_type: str
    action: str           # "classify_email", "draft_response", etc.
    input_summary: str    # Truncated input
    output_summary: str   # Truncated output
    decision: str         # What was decided
    confidence: float     # 0-1
    escalated: bool       # Did it go to human?
    authorized_by: str    # "agent" or user_id
    trace_id: str         # Langfuse trace
```

### 3. Escalation Pattern

```python
# Escalar a humano cuando confianza < threshold
async def maybe_escalate(result: AgentResult, threshold: float = 0.8):
    if result.confidence < threshold:
        await slack_notify(
            user_id=result.user_id,
            message=f"Need your input: {result.summary}",
            actions=[
                {"text": "Approve", "value": "approve"},
                {"text": "Reject", "value": "reject"},
                {"text": "Edit", "value": "edit"}
            ]
        )
        # Workflow pauses until human responds
        return await wait_for_human_response(result.workflow_id)
    return result
```

### 4. LLM Provider Abstraction

```python
# Routing por tipo de task
class LLMRouter:
    ROUTING = {
        "classify": ("gpt-4o-mini", "claude-3-haiku"),      # Fast, cheap
        "generate": ("claude-3-5-sonnet", "gpt-4o"),        # Quality
        "analyze": ("claude-3-opus", "gpt-4o"),             # Complex
    }

    async def call(self, task_type: str, prompt: str) -> str:
        primary, fallback = self.ROUTING[task_type]
        try:
            return await self._call_provider(primary, prompt)
        except ProviderError:
            return await self._call_provider(fallback, prompt)
```

## Data Flow: InboxPilot Example

```
1. Gmail Webhook → FastAPI /webhooks/gmail
2. API validates & queues → Celery task
3. Worker picks up → InboxPilotAgent.run()
4. Agent fetches full email → Gmail API
5. Agent classifies → LLM (GPT-4o-mini)
6. If important: draft response → LLM (Claude Sonnet)
7. If confidence < 80%: escalate → Slack notification
8. Human approves/edits → Slack action
9. Agent sends/archives → Gmail API
10. Audit log written → PostgreSQL
11. Trace completed → Langfuse
```

## Security

| Aspect | Implementation |
|--------|----------------|
| Auth | JWT (24h) + Refresh tokens + Google OAuth |
| Secrets | AWS Secrets Manager |
| Encryption | HTTPS only, encrypted at rest (RDS) |
| Input validation | Pydantic on all endpoints |
| SQL injection | SQLAlchemy ORM (parameterized queries) |
| Rate limiting | FastAPI middleware + Redis |
| Audit | Immutable audit_log table |

## Non-Functional Requirements

| Aspect | Target | Notes |
|--------|--------|-------|
| API Response | < 200ms p95 | Excluding LLM calls |
| LLM Response | < 10s p95 | With streaming where possible |
| Availability | 99.5% | MVP target |
| Workflow completion | 99% | With retries |
| Data retention | 1 year | Audit logs |
| Concurrent users | 100 | MVP scale |

## Cost Estimation (MVP)

| Service | Monthly Cost |
|---------|--------------|
| ECS Fargate (API + 2 workers) | ~$50 |
| RDS PostgreSQL (db.t3.micro) | ~$15 |
| ElastiCache Redis (cache.t3.micro) | ~$12 |
| Langfuse (self-hosted or free tier) | $0 |
| LLM APIs | ~$50-100 (usage dependent) |
| Vercel (frontend) | $0 (hobby) |
| **Total** | **~$130-180/month** |

---

*Last updated: 2026-01-31*
*ADRs: [View all](../decisions/)*
*MVP Features: [View dashboard](../features/_index.md)*
*Next step: `/interview FEAT-001`*
