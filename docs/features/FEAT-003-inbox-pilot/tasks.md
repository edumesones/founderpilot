# FEAT-003: InboxPilot - Tasks

## Pre-Implementation Checklist
- [x] spec.md complete and approved
- [x] design.md complete and approved
- [x] Branch created: `feat/FEAT-003`
- [x] status.md updated to "In Progress"

---

## Phase 1: Foundation (Day 1-2)

| # | Task | Status |
|---|------|--------|
| 1.1 | Create project file structure | ✅ |
| 1.2 | Create database models | ✅ |
| 1.3 | Create Alembic migration | ✅ |
| 1.4 | Create Pydantic schemas | ✅ |

### Detailed Tasks

- [x] **1.1**: Create directory structure
  - [x] 1.1.1: `src/agents/inbox_pilot/` with `__init__.py`
  - [x] 1.1.2: `src/agents/inbox_pilot/nodes/` with `__init__.py`
  - [x] 1.1.3: `src/agents/inbox_pilot/prompts/` with `__init__.py`
  - [x] 1.1.4: `src/integrations/gmail/` with `__init__.py`
  - [x] 1.1.5: `src/models/inbox_pilot/` with `__init__.py`
  - [x] 1.1.6: `src/schemas/inbox_pilot/` with `__init__.py`
  - [x] 1.1.7: `src/services/inbox_pilot/` with `__init__.py`
  - [x] 1.1.8: `tests/unit/agents/inbox_pilot/`
  - [x] 1.1.9: `tests/fixtures/emails/`

- [x] **1.2**: Create SQLAlchemy models
  - [x] 1.2.1: `src/models/inbox_pilot/email_record.py` - EmailRecord model
  - [x] 1.2.2: `src/models/inbox_pilot/agent_config.py` - InboxPilotConfig model
  - [x] 1.2.3: Export models in `__init__.py`

- [x] **1.3**: Create database migration
  - [x] 1.3.1: Generate Alembic migration for `email_records` table
  - [x] 1.3.2: Add `inbox_pilot_configs` table to migration
  - [x] 1.3.3: Add indexes

- [x] **1.4**: Create Pydantic schemas
  - [x] 1.4.1: `src/schemas/inbox_pilot/email.py` - EmailDTO, EmailList
  - [x] 1.4.2: `src/schemas/inbox_pilot/classification.py` - ClassificationResult
  - [x] 1.4.3: `src/schemas/inbox_pilot/config.py` - ConfigCreate, ConfigUpdate, ConfigResponse

---

## Phase 2: Gmail Integration (Day 2-3)

| # | Task | Status |
|---|------|--------|
| 2.1 | Create Gmail client wrapper | ✅ |
| 2.2 | Create Pub/Sub webhook handler | ✅ |
| 2.3 | Create Gmail labels manager | ✅ |
| 2.4 | Add webhook endpoint | ✅ |

### Detailed Tasks

- [x] **2.1**: Gmail API client
  - [x] 2.1.1: `src/integrations/gmail/client.py` - GmailClient class
  - [x] 2.1.2: Implement `get_message()` with thread context
  - [x] 2.1.3: Implement `send_reply()`
  - [x] 2.1.4: Implement `archive()`
  - [x] 2.1.5: Implement `setup_watch()` for push notifications
  - [x] 2.1.6: Token refresh handling

- [x] **2.2**: Webhook handler
  - [x] 2.2.1: `src/integrations/gmail/webhook.py` - parse Pub/Sub message
  - [x] 2.2.2: Signature validation (placeholder)
  - [x] 2.2.3: Extract history_id and user email

- [x] **2.3**: Labels manager
  - [x] 2.3.1: Labels included in GmailClient
  - [x] 2.3.2: Create FP_Urgent, FP_Important, FP_Routine, FP_Spam labels
  - [x] 2.3.3: `add_label()` method

- [x] **2.4**: Webhook endpoint
  - [x] 2.4.1: `src/api/routes/webhooks.py` - POST /webhooks/gmail
  - [x] 2.4.2: Queue email processing in background

---

## Phase 3: Agent Core (Day 3-5)

| # | Task | Status |
|---|------|--------|
| 3.1 | Create state definition | ✅ |
| 3.2 | Create LangGraph agent | ✅ |
| 3.3 | Implement fetch node | ✅ |
| 3.4 | Implement classify node | ✅ |
| 3.5 | Implement draft node | ✅ |
| 3.6 | Create prompts | ✅ |

### Detailed Tasks

- [x] **3.1**: State definition
  - [x] 3.1.1: `src/agents/inbox_pilot/state.py` - InboxState TypedDict
  - [x] 3.1.2: EmailData, ClassificationResult, DraftResult TypedDicts

- [x] **3.2**: LangGraph agent
  - [x] 3.2.1: `src/agents/inbox_pilot/agent.py` - InboxPilotAgent class
  - [x] 3.2.2: `_build_graph()` with all nodes and edges
  - [x] 3.2.3: `run()` method
  - [x] 3.2.4: `resume()` method for human-in-loop

- [x] **3.3**: Fetch node
  - [x] 3.3.1: `src/agents/inbox_pilot/nodes/fetch.py` - fetch_email()
  - [x] 3.3.2: Parse email headers, body, attachments metadata
  - [x] 3.3.3: Get thread context (last 5 messages)

- [x] **3.4**: Classify node
  - [x] 3.4.1: `src/agents/inbox_pilot/nodes/classify.py` - classify()
  - [x] 3.4.2: Call LLM with classification prompt
  - [x] 3.4.3: Parse JSON response to ClassificationResult

- [x] **3.5**: Draft node
  - [x] 3.5.1: `src/agents/inbox_pilot/nodes/draft.py` - draft_response()
  - [x] 3.5.2: Call LLM with draft prompt
  - [x] 3.5.3: Parse JSON response to DraftResult

- [x] **3.6**: Prompts
  - [x] 3.6.1: `src/agents/inbox_pilot/prompts/classify.py` - CLASSIFICATION_SYSTEM_PROMPT
  - [x] 3.6.2: `build_classification_prompt()` function
  - [x] 3.6.3: `src/agents/inbox_pilot/prompts/draft.py` - DRAFT_SYSTEM_PROMPT
  - [x] 3.6.4: `build_draft_prompt()` function

---

## Phase 4: Escalation (Day 5-6)

| # | Task | Status |
|---|------|--------|
| 4.1 | Implement escalate node | ✅ |
| 4.2 | Create Slack notification | ✅ |
| 4.3 | Handle Slack actions | ✅ |
| 4.4 | Implement execute node | ✅ |

### Detailed Tasks

- [x] **4.1**: Escalate node
  - [x] 4.1.1: `src/agents/inbox_pilot/nodes/escalate.py` - escalate()
  - [x] 4.1.2: Build Slack message blocks
  - [x] 4.1.3: Include draft preview if available

- [x] **4.2**: Slack notification
  - [x] 4.2.1: Create Slack Block Kit message template
  - [x] 4.2.2: Add action buttons: Approve, Edit, Reject, Archive
  - [x] 4.2.3: Include email metadata and classification

- [x] **4.3**: Slack action handler
  - [x] 4.3.1: Handle `inbox_pilot_approve` action
  - [x] 4.3.2: Handle `inbox_pilot_reject` action
  - [x] 4.3.3: Handle `inbox_pilot_edit` action with modal
  - [x] 4.3.4: Handle `inbox_pilot_archive` action
  - [x] 4.3.5: Call agent.resume() with human decision

- [x] **4.4**: Execute node
  - [x] 4.4.1: `src/agents/inbox_pilot/nodes/execute.py` - execute_action()
  - [x] 4.4.2: Send reply via Gmail
  - [x] 4.4.3: Archive email if needed
  - [x] 4.4.4: Apply Gmail label

---

## Phase 5: API & Service (Day 6-7)

| # | Task | Status |
|---|------|--------|
| 5.1 | Create service layer | ✅ |
| 5.2 | Create API endpoints | ✅ |
| 5.3 | Create Celery task | ⏭️ |

### Detailed Tasks

- [x] **5.1**: Service layer
  - [x] 5.1.1: `src/services/inbox_pilot/service.py` - InboxPilotService
  - [x] 5.1.2: `process_email()` - main entry point
  - [x] 5.1.3: `handle_slack_action()` - Slack callback handler
  - [x] 5.1.4: `get_config()`, `update_config()`
  - [x] 5.1.5: `setup_watch()`, `stop_watch()`
  - [x] 5.1.6: `list_emails()`, `get_email()`

- [x] **5.2**: API endpoints
  - [x] 5.2.1: `src/api/routes/inbox_pilot.py` - router
  - [x] 5.2.2: GET `/api/v1/inbox-pilot/config`
  - [x] 5.2.3: PUT `/api/v1/inbox-pilot/config`
  - [x] 5.2.4: GET `/api/v1/inbox-pilot/emails`
  - [x] 5.2.5: GET `/api/v1/inbox-pilot/emails/{id}`
  - [x] 5.2.6: POST `/api/v1/inbox-pilot/emails/{id}/action`
  - [x] 5.2.7: POST `/api/v1/inbox-pilot/watch`
  - [x] 5.2.8: DELETE `/api/v1/inbox-pilot/watch`

- [x] **5.3**: Celery task ⏭️ DEFERRED - Using FastAPI BackgroundTasks
  - [x] 5.3.1: Background tasks via FastAPI (no Celery for MVP)
  - [ ] 5.3.2: Error handling and retries - deferred
  - [ ] 5.3.3: Rate limiting - deferred

---

## Phase 6: Testing (Day 7-8)

| # | Task | Status |
|---|------|--------|
| 6.1 | Unit tests - nodes | ✅ |
| 6.2 | Unit tests - service | ✅ |
| 6.3 | Integration tests | ✅ |
| 6.4 | Test fixtures | ✅ |

### Detailed Tasks

- [x] **6.1**: Unit tests for nodes
  - [x] 6.1.1: `tests/unit/agents/inbox_pilot/test_classify.py`
  - [x] 6.1.2: `tests/unit/agents/inbox_pilot/test_draft.py`
  - [x] 6.1.3: `tests/unit/agents/inbox_pilot/test_state.py`

- [x] **6.2**: Unit tests for service
  - [x] 6.2.1: `tests/unit/services/test_inbox_pilot_service.py`
  - [x] 6.2.2: Test idempotency
  - [x] 6.2.3: Test config CRUD

- [x] **6.3**: Integration tests
  - [x] 6.3.1: `tests/integration/test_inbox_pilot_agent.py`
  - [x] 6.3.2: Test full happy path flow
  - [x] 6.3.3: Test escalation flow
  - [x] 6.3.4: Test VIP routing

- [x] **6.4**: Test fixtures
  - [x] 6.4.1: `tests/conftest.py` with fixtures
  - [x] 6.4.2: sample_email, urgent_email, spam_email fixtures
  - [x] 6.4.3: classification and draft fixtures

---

## Phase 7: Polish (Day 8)

| # | Task | Status |
|---|------|--------|
| 7.1 | Error handling | ✅ |
| 7.2 | Logging | ✅ |
| 7.3 | Documentation | ✅ |

### Detailed Tasks

- [x] **7.1**: Error handling
  - [x] 7.1.1: Gmail API error handling (rate limits, auth errors)
  - [x] 7.1.2: LLM API error handling (fallback, retry)
  - [x] 7.1.3: Graceful degradation (escalate on error)

- [x] **7.2**: Logging
  - [x] 7.2.1: Structured logging module (src/core/logging.py)
  - [x] 7.2.2: Langfuse tracing setup (src/core/tracing.py)
  - [x] 7.2.3: AgentLogger with specialized methods

- [x] **7.3**: Documentation
  - [x] 7.3.1: .env.example created
  - [x] 7.3.2: Docstrings on all public functions
  - [x] 7.3.3: Type hints throughout codebase

---

## Progress Tracking

### Status Legend
| Symbol | Meaning |
|--------|---------|
| `⬜` | Pending |
| `🟡` | In Progress |
| `✅` | Completed |
| `🔴` | Blocked |
| `⏭️` | Skipped |

### Current Progress

| Phase | Done | Total | % |
|-------|------|-------|---|
| Phase 1: Foundation | 4 | 4 | 100% |
| Phase 2: Gmail | 4 | 4 | 100% |
| Phase 3: Agent | 6 | 6 | 100% |
| Phase 4: Escalation | 4 | 4 | 100% |
| Phase 5: API | 3 | 3 | 100% |
| Phase 6: Testing | 4 | 4 | 100% |
| Phase 7: Polish | 3 | 3 | 100% |
| **TOTAL** | **28** | **28** | **100%** |

---

## Notes

### Files Created
- 50+ Python source files
- 2 Alembic migrations
- pyproject.toml with dependencies
- .env.example with configuration
- Comprehensive unit and integration tests
- Structured logging and tracing modules

### Completed Work
- Full LangGraph agent with human-in-loop
- Gmail and Slack integrations
- REST API with all endpoints
- Unit tests for service layer
- Integration tests for agent flows
- Structured logging (structlog)
- Langfuse tracing setup

### Technical Debt
- Celery task deferred - using FastAPI background tasks for MVP
- PostgresSaver checkpointer placeholder - needs proper setup
- Pub/Sub signature validation placeholder

---

*Last updated: 2026-01-31*
*Updated by: Ralph Loop*
