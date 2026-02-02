# FEAT-005: MeetingPilot - Tasks

## Pre-Implementation Checklist
- [x] spec.md complete and approved
- [x] analysis.md complete (Medium-High confidence)
- [x] design.md complete and approved
- [ ] Branch created: `feat/FEAT-005` (already on branch)
- [ ] status.md updated to "In Progress"

---

## Phase 1: Foundation (Tasks 1-4)

### Database & Models

- [x] **T1**: Create database migration for MeetingPilot tables
  - [x] T1.1: Create `meeting_records` table with indexes
  - [x] T1.2: Create `meeting_notes` table with FK
  - [x] T1.3: Create `meeting_pilot_configs` table
  - [⏭️] T1.4: Run migration, verify schema (skip - no DB in dev)

- [x] **T2**: Create SQLAlchemy models
  - [x] T2.1: `src/models/meeting_pilot/meeting_record.py`
  - [x] T2.2: `src/models/meeting_pilot/meeting_note.py`
  - [x] T2.3: `src/models/meeting_pilot/agent_config.py`
  - [x] T2.4: `src/models/meeting_pilot/__init__.py` exports
  - [x] T2.5: Update `src/models/__init__.py`

### Calendar Integration

- [x] **T3**: Create Google Calendar client
  - [x] T3.1: `src/integrations/calendar/__init__.py`
  - [x] T3.2: `src/integrations/calendar/client.py` - CalendarClient class
  - [x] T3.3: Implement `list_events()` method
  - [x] T3.4: Implement `get_event()` method
  - [x] T3.5: Implement `parse_attendees()` helper

- [x] **T4**: Create Pydantic schemas
  - [x] T4.1: `src/schemas/meeting_pilot/meeting.py` - MeetingRecord schemas
  - [x] T4.2: `src/schemas/meeting_pilot/brief.py` - Brief schemas
  - [x] T4.3: `src/schemas/meeting_pilot/config.py` - Config schemas
  - [x] T4.4: `src/schemas/meeting_pilot/__init__.py` exports

---

## Phase 2: Agent Core (Tasks 5-9)

### State & Agent Structure

- [x] **T5**: Create MeetingState TypedDict
  - [x] T5.1: `src/agents/meeting_pilot/state.py`
  - [x] T5.2: Define all state fields (meeting, context, brief, notes, etc.)
  - [x] T5.3: Define helper TypedDicts (AttendeeData, BriefResult, etc.)

- [x] **T6**: Create agent node functions
  - [x] T6.1: `src/agents/meeting_pilot/nodes/__init__.py`
  - [x] T6.2: `src/agents/meeting_pilot/nodes/fetch.py` - fetch_meeting node
  - [x] T6.3: `src/agents/meeting_pilot/nodes/context.py` - gather_context node
  - [x] T6.4: `src/agents/meeting_pilot/nodes/brief.py` - generate_brief node
  - [x] T6.5: `src/agents/meeting_pilot/nodes/notify.py` - notify_slack node
  - [x] T6.6: `src/agents/meeting_pilot/nodes/notes.py` - capture_notes node
  - [x] T6.7: `src/agents/meeting_pilot/nodes/followup.py` - suggest_followup node

### LLM Prompts

- [x] **T7**: Create brief generation prompt
  - [x] T7.1: `src/agents/meeting_pilot/prompts/__init__.py`
  - [x] T7.2: `src/agents/meeting_pilot/prompts/brief.py` - BRIEF_SYSTEM_PROMPT
  - [x] T7.3: Create prompt template for meeting context

### Agent Assembly

- [x] **T8**: Create MeetingPilotAgent class
  - [x] T8.1: `src/agents/meeting_pilot/__init__.py`
  - [x] T8.2: `src/agents/meeting_pilot/agent.py` - MeetingPilotAgent
  - [x] T8.3: Implement `_build_graph()` with StateGraph
  - [x] T8.4: Add routing functions (_route_after_brief)
  - [x] T8.5: Implement `run()` method
  - [x] T8.6: Implement `resume()` method for human input

- [x] **T9**: Create MeetingPilotService
  - [x] T9.1: `src/services/meeting_pilot/__init__.py`
  - [x] T9.2: `src/services/meeting_pilot/service.py`
  - [x] T9.3: Implement `sync_calendar()` method
  - [x] T9.4: Implement `get_meetings_needing_briefs()` method
  - [x] T9.5: Implement `mark_brief_sent()` method
  - [x] T9.6: Implement `add_note()` method

---

## Phase 3: Notifications (Tasks 10-12)

### Slack Integration

- [ ] **T10**: Create Slack blocks for meeting brief
  - [ ] T10.1: Add `build_meeting_brief_blocks()` to `src/integrations/slack/blocks.py`
  - [ ] T10.2: Add meeting header block
  - [ ] T10.3: Add participants section
  - [ ] T10.4: Add brief content section
  - [ ] T10.5: Add action buttons (Add Note, Snooze, Skip)

- [ ] **T11**: Add Slack action handlers
  - [ ] T11.1: Add `meeting_add_note` handler to `src/integrations/slack/handlers.py`
  - [ ] T11.2: Add `meeting_snooze` handler
  - [ ] T11.3: Add `meeting_skip` handler
  - [ ] T11.4: Add modal for note input

- [ ] **T12**: Implement brief notification flow
  - [ ] T12.1: Add `send_brief_notification()` to service
  - [ ] T12.2: Handle DM-only delivery
  - [ ] T12.3: Add error handling for Slack failures

---

## Phase 4: Scheduling (Tasks 13-15)

### Celery Tasks

- [ ] **T13**: Create Celery tasks for MeetingPilot
  - [ ] T13.1: `src/workers/tasks/meeting_tasks.py`
  - [ ] T13.2: `sync_all_calendars` task
  - [ ] T13.3: `process_user_meetings` task
  - [ ] T13.4: `send_meeting_brief` task

- [ ] **T14**: Configure Celery Beat schedule
  - [ ] T14.1: Add meeting sync to beat schedule (every 15 min)
  - [ ] T14.2: Add meeting brief check (every 5 min)
  - [ ] T14.3: Update `src/workers/celery_app.py`

- [ ] **T15**: Add sync job health monitoring
  - [ ] T15.1: Add last_sync_at tracking
  - [ ] T15.2: Add sync failure alerting
  - [ ] T15.3: Add health check endpoint

---

## Phase 5: API & Config (Tasks 16-18)

### REST API

- [ ] **T16**: Create API routes
  - [ ] T16.1: `src/api/routes/meeting_pilot.py`
  - [ ] T16.2: GET `/meetings` - list upcoming meetings
  - [ ] T16.3: GET `/meetings/{id}` - get meeting with brief
  - [ ] T16.4: POST `/meetings/{id}/notes` - add note
  - [ ] T16.5: GET `/config` - get user config
  - [ ] T16.6: PUT `/config` - update user config
  - [ ] T16.7: POST `/sync` - trigger manual sync

- [ ] **T17**: Register router and add dependencies
  - [ ] T17.1: Update `src/api/main.py` to include meeting_pilot router
  - [ ] T17.2: Add get_current_user dependency
  - [ ] T17.3: Add get_calendar_client dependency

- [ ] **T18**: Add config settings
  - [ ] T18.1: Add GOOGLE_CALENDAR_* settings to `src/core/config.py`
  - [ ] T18.2: Add calendar scopes to OAuth flow
  - [ ] T18.3: Update .env.example

---

## Phase 6: Testing (Tasks 19-22)

### Unit Tests

- [ ] **T19**: Test agent state and nodes
  - [ ] T19.1: `tests/unit/agents/meeting_pilot/test_state.py`
  - [ ] T19.2: `tests/unit/agents/meeting_pilot/nodes/test_fetch.py`
  - [ ] T19.3: `tests/unit/agents/meeting_pilot/nodes/test_context.py`
  - [ ] T19.4: `tests/unit/agents/meeting_pilot/nodes/test_brief.py`

- [ ] **T20**: Test service layer
  - [ ] T20.1: `tests/unit/services/test_meeting_pilot_service.py`
  - [ ] T20.2: Test sync_calendar with mock Calendar API
  - [ ] T20.3: Test process_upcoming_meetings
  - [ ] T20.4: Test generate_brief with mock LLM

- [ ] **T21**: Test calendar client
  - [ ] T21.1: `tests/unit/integrations/test_calendar_client.py`
  - [ ] T21.2: Test list_events
  - [ ] T21.3: Test parse_attendees

### Integration Tests

- [ ] **T22**: Integration tests for API
  - [ ] T22.1: `tests/integration/test_meeting_pilot_api.py`
  - [ ] T22.2: Test GET /meetings endpoint
  - [ ] T22.3: Test POST /notes endpoint
  - [ ] T22.4: Test PUT /config endpoint

---

## Phase 7: Polish (Tasks 23-25)

### Error Handling & Audit

- [ ] **T23**: Implement comprehensive error handling
  - [ ] T23.1: Add CalendarDisconnectedError exception
  - [ ] T23.2: Add rate limit handling with backoff
  - [ ] T23.3: Add graceful LLM timeout handling
  - [ ] T23.4: Add audit log entries for all agent actions

- [ ] **T24**: Add observability
  - [ ] T24.1: Add Langfuse tracing to brief generation
  - [ ] T24.2: Add metrics for sync job
  - [ ] T24.3: Add logging throughout

- [ ] **T25**: Final cleanup and documentation
  - [ ] T25.1: Add docstrings to all public functions
  - [ ] T25.2: Update tests.md with test results
  - [ ] T25.3: Final code review pass
  - [ ] T25.4: Update status.md to complete

---

## Progress Tracking

### Status Legend
| Symbol | Meaning |
|--------|---------|
| `- [ ]` | Pending |
| `- [🟡]` | In Progress |
| `- [x]` | Completed |
| `- [🔴]` | Blocked |
| `- [⏭️]` | Skipped |

### Current Progress

| Phase | Done | Total | % |
|-------|------|-------|---|
| Phase 1: Foundation | 4 | 4 | 100% |
| Phase 2: Agent Core | 5 | 5 | 100% |
| Phase 3: Notifications | 0 | 3 | 0% |
| Phase 4: Scheduling | 0 | 3 | 0% |
| Phase 5: API & Config | 0 | 3 | 0% |
| Phase 6: Testing | 0 | 4 | 0% |
| Phase 7: Polish | 0 | 3 | 0% |
| **TOTAL** | **9** | **25** | **36%** |

---

## Notes

### Blockers
_None currently_

### Decisions Made During Implementation
_Document any decisions made while implementing_

### Technical Debt
_Track any shortcuts taken that need future work_

---

*Last updated: 2026-02-02*
*Updated by: Ralph Loop*
