# FEAT-005: MeetingPilot - Technical Design

## Overview

MeetingPilot es un agente LangGraph que prepara a founders para sus meetings. Sincroniza con Google Calendar, detecta meetings proximos, recopila contexto de Gmail, genera briefs pre-meeting via Slack, y facilita captura de notas post-meeting.

**Patron arquitectonico:** Consistente con InboxPilot - LangGraph StateGraph con human-in-loop.

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MeetingPilot Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────┐                                                      │
│   │  Celery Beat     │──── Every 15 min ────┐                              │
│   │  (Scheduler)     │                      │                              │
│   └──────────────────┘                      ▼                              │
│                                    ┌──────────────────┐                     │
│   ┌──────────────────┐            │ MeetingPilot     │                     │
│   │  Google Calendar │◄──────────▶│ Service          │                     │
│   │  API             │   sync     │                  │                     │
│   └──────────────────┘            └────────┬─────────┘                     │
│                                            │                               │
│   ┌──────────────────┐            ┌────────▼─────────┐                     │
│   │  Gmail API       │◄──────────▶│ MeetingPilot     │                     │
│   │  (context)       │   fetch    │ Agent (LangGraph)│                     │
│   └──────────────────┘            │                  │                     │
│                                   │ ┌──────────────┐ │                     │
│   ┌──────────────────┐            │ │ sync_calendar│ │                     │
│   │  PostgreSQL      │◄──────────▶│ │ detect_mtgs  │ │                     │
│   │  - meetings      │   persist  │ │ gather_ctx   │ │                     │
│   │  - meeting_notes │            │ │ gen_brief    │ │                     │
│   │  - audit_log     │            │ │ notify_slack │ │                     │
│   └──────────────────┘            │ │ human_review │ │                     │
│                                   │ │ capture_notes│ │                     │
│   ┌──────────────────┐            │ │ follow_up    │ │                     │
│   │  Slack Bot       │◄──────────▶│ │ audit_log    │ │                     │
│   │  (notifications) │   notify   │ └──────────────┘ │                     │
│   └──────────────────┘            └──────────────────┘                     │
│                                                                             │
│   ┌──────────────────┐            ┌──────────────────┐                     │
│   │  LLM (Haiku)     │◄──────────▶│  Langfuse        │                     │
│   │  (brief gen)     │   trace    │  (observability) │                     │
│   └──────────────────┘            └──────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Graph Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MeetingPilot LangGraph StateGraph                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ENTRY                                                                      │
│    │                                                                        │
│    ▼                                                                        │
│  [fetch_meeting] ──────► Get meeting details from calendar                  │
│    │                                                                        │
│    ▼                                                                        │
│  [gather_context] ──────► Query emails with participants                    │
│    │                                                                        │
│    ▼                                                                        │
│  [generate_brief] ──────► LLM creates meeting brief                         │
│    │                                                                        │
│    ├───► confidence < 0.8? ───► [escalate]                                 │
│    │                              │                                         │
│    ▼                              │                                         │
│  [notify_slack] ◄─────────────────┘                                        │
│    │                                                                        │
│    ▼                                                                        │
│  [human_review] ◄───── interrupt_before (wait for meeting end)             │
│    │                                                                        │
│    ▼                                                                        │
│  [capture_notes] ──────► Post-meeting notes input                          │
│    │                                                                        │
│    ▼                                                                        │
│  [suggest_followup] ──────► LLM suggests action items                      │
│    │                                                                        │
│    ▼                                                                        │
│  [audit_log] ──────► Record all actions                                    │
│    │                                                                        │
│    ▼                                                                        │
│   END                                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

### New Files to Create

```
src/
├── agents/
│   └── meeting_pilot/
│       ├── __init__.py
│       ├── agent.py              # LangGraph StateGraph
│       ├── state.py              # MeetingState TypedDict
│       ├── nodes/
│       │   ├── __init__.py
│       │   ├── fetch.py          # Fetch meeting details
│       │   ├── context.py        # Gather email context
│       │   ├── brief.py          # Generate brief
│       │   ├── notify.py         # Slack notification
│       │   ├── notes.py          # Capture notes
│       │   └── followup.py       # Suggest follow-ups
│       └── prompts/
│           ├── __init__.py
│           └── brief.py          # Brief generation prompt
│
├── integrations/
│   └── calendar/
│       ├── __init__.py
│       └── client.py             # Google Calendar client
│
├── models/
│   └── meeting_pilot/
│       ├── __init__.py
│       ├── meeting_record.py     # MeetingRecord model
│       ├── meeting_note.py       # MeetingNote model
│       └── agent_config.py       # MeetingPilotConfig model
│
├── schemas/
│   └── meeting_pilot/
│       ├── __init__.py
│       ├── meeting.py            # Meeting schemas
│       ├── brief.py              # Brief schemas
│       └── config.py             # Config schemas
│
├── services/
│   └── meeting_pilot/
│       ├── __init__.py
│       └── service.py            # MeetingPilotService
│
├── api/
│   └── routes/
│       └── meeting_pilot.py      # API endpoints
│
└── workers/
    └── tasks/
        └── meeting_tasks.py      # Celery tasks

tests/
├── unit/
│   ├── agents/
│   │   └── meeting_pilot/
│   │       ├── test_agent.py
│   │       ├── test_state.py
│   │       └── nodes/
│   │           ├── test_fetch.py
│   │           ├── test_context.py
│   │           └── test_brief.py
│   └── services/
│       └── test_meeting_pilot_service.py
└── integration/
    └── test_meeting_pilot_api.py

alembic/
└── versions/
    └── xxx_add_meeting_pilot_tables.py
```

### Files to Modify

| File | Changes |
|------|---------|
| `src/api/main.py` | Add meeting_pilot router |
| `src/core/config.py` | Add GOOGLE_CALENDAR_* settings |
| `src/models/__init__.py` | Export meeting_pilot models |
| `src/workers/celery_app.py` | Add meeting sync task to beat schedule |
| `src/integrations/slack/blocks.py` | Add meeting brief blocks |
| `src/integrations/slack/handlers.py` | Add meeting action handlers |
| `requirements.txt` | No new deps (google-api-python-client already exists) |

---

## Data Model

### Entities

```python
# MeetingRecord - Synced calendar events
class MeetingRecord(Base):
    __tablename__ = "meeting_records"

    id: UUID                          # Primary key
    tenant_id: UUID                   # Multi-tenant
    user_id: UUID                     # Owner
    calendar_event_id: str            # Google Calendar event ID
    title: str                        # Meeting title
    description: Optional[str]        # Meeting description
    start_time: datetime              # Meeting start
    end_time: datetime                # Meeting end
    location: Optional[str]           # Location/link
    attendees: List[dict]             # [{email, name, response_status}]
    is_external: bool                 # Has non-org attendees
    brief_sent_at: Optional[datetime] # When brief was sent
    brief_content: Optional[str]      # Generated brief
    status: str                       # pending, brief_sent, completed, cancelled
    created_at: datetime
    updated_at: datetime

# MeetingNote - User notes for meetings
class MeetingNote(Base):
    __tablename__ = "meeting_notes"

    id: UUID                          # Primary key
    meeting_id: UUID                  # FK to meeting_records
    user_id: UUID                     # Who wrote the note
    content: str                      # Note content
    note_type: str                    # pre_meeting, post_meeting, action_item
    created_at: datetime

# MeetingPilotConfig - Per-user configuration
class MeetingPilotConfig(Base):
    __tablename__ = "meeting_pilot_configs"

    id: UUID                          # Primary key
    user_id: UUID                     # FK to users, unique
    is_enabled: bool                  # Agent enabled
    brief_minutes_before: int         # Default 30
    only_external_meetings: bool      # Default True
    min_attendees: int                # Default 1
    escalation_threshold: float       # Default 0.8
    created_at: datetime
    updated_at: datetime
```

### Database Schema

```sql
-- Migration: add_meeting_pilot_tables

CREATE TABLE meeting_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID NOT NULL REFERENCES users(id),
    calendar_event_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    location VARCHAR(500),
    attendees JSONB DEFAULT '[]',
    is_external BOOLEAN DEFAULT FALSE,
    brief_sent_at TIMESTAMPTZ,
    brief_content TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, calendar_event_id)
);

CREATE INDEX idx_meeting_records_user_start ON meeting_records(user_id, start_time);
CREATE INDEX idx_meeting_records_status ON meeting_records(status) WHERE status = 'pending';

CREATE TABLE meeting_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meeting_records(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    note_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meeting_notes_meeting ON meeting_notes(meeting_id);

CREATE TABLE meeting_pilot_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id),
    is_enabled BOOLEAN DEFAULT TRUE,
    brief_minutes_before INTEGER DEFAULT 30,
    only_external_meetings BOOLEAN DEFAULT TRUE,
    min_attendees INTEGER DEFAULT 1,
    escalation_threshold NUMERIC(3,2) DEFAULT 0.80,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Design

### Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/meeting-pilot/meetings` | List upcoming meetings | JWT |
| GET | `/api/v1/meeting-pilot/meetings/{id}` | Get meeting with brief | JWT |
| POST | `/api/v1/meeting-pilot/meetings/{id}/notes` | Add note to meeting | JWT |
| GET | `/api/v1/meeting-pilot/config` | Get user config | JWT |
| PUT | `/api/v1/meeting-pilot/config` | Update user config | JWT |
| POST | `/api/v1/meeting-pilot/sync` | Trigger manual sync | JWT |

### Request/Response Examples

```json
// GET /api/v1/meeting-pilot/meetings
// Response 200
{
  "meetings": [
    {
      "id": "uuid",
      "title": "Weekly sync with Client X",
      "start_time": "2026-02-03T10:00:00Z",
      "end_time": "2026-02-03T11:00:00Z",
      "attendees": [
        {"email": "john@client.com", "name": "John Smith"}
      ],
      "is_external": true,
      "status": "pending",
      "brief_sent_at": null
    }
  ],
  "total": 1
}

// POST /api/v1/meeting-pilot/meetings/{id}/notes
// Request
{
  "content": "Discutimos pricing, quedaron en revisar propuesta",
  "note_type": "post_meeting"
}

// Response 201
{
  "id": "uuid",
  "meeting_id": "uuid",
  "content": "Discutimos pricing...",
  "note_type": "post_meeting",
  "created_at": "2026-02-03T11:30:00Z"
}

// PUT /api/v1/meeting-pilot/config
// Request
{
  "brief_minutes_before": 45,
  "only_external_meetings": true
}

// Response 200
{
  "id": "uuid",
  "is_enabled": true,
  "brief_minutes_before": 45,
  "only_external_meetings": true,
  "min_attendees": 1,
  "escalation_threshold": 0.8
}
```

---

## Service Layer

### MeetingPilotService

```python
class MeetingPilotService:
    """Orchestrates MeetingPilot operations."""

    def __init__(
        self,
        db: AsyncSession,
        calendar_client: CalendarClient,
        gmail_client: GmailClient,
        slack_notifier: SlackNotifier,
        llm_router: LLMRouter,
    ):
        self.db = db
        self.calendar = calendar_client
        self.gmail = gmail_client
        self.slack = slack_notifier
        self.llm = llm_router

    async def sync_calendar(self, user_id: UUID) -> int:
        """Sync calendar events for user. Returns count of new meetings."""
        pass

    async def process_upcoming_meetings(self, user_id: UUID) -> List[MeetingRecord]:
        """Find meetings needing briefs and process them."""
        pass

    async def generate_brief(self, meeting: MeetingRecord) -> BriefResult:
        """Generate meeting brief with context."""
        pass

    async def send_brief_notification(self, meeting: MeetingRecord, brief: str) -> bool:
        """Send brief to user via Slack."""
        pass

    async def add_note(self, meeting_id: UUID, user_id: UUID, content: str, note_type: str) -> MeetingNote:
        """Add note to meeting."""
        pass

    async def suggest_followups(self, meeting_id: UUID) -> List[str]:
        """Suggest follow-up actions based on notes."""
        pass
```

### CalendarClient

```python
class CalendarClient:
    """Google Calendar API client."""

    def __init__(self, credentials: Credentials):
        self.service = build('calendar', 'v3', credentials=credentials)

    async def list_events(
        self,
        time_min: datetime,
        time_max: datetime,
        calendar_id: str = 'primary'
    ) -> List[dict]:
        """List calendar events in time range."""
        pass

    async def get_event(self, event_id: str, calendar_id: str = 'primary') -> dict:
        """Get single event by ID."""
        pass

    def parse_attendees(self, event: dict) -> List[dict]:
        """Parse attendees from event, identify external."""
        pass
```

---

## Slack Integration

### Meeting Brief Block Kit

```python
def build_meeting_brief_blocks(meeting: MeetingRecord, brief: BriefResult) -> List[dict]:
    """Build Slack Block Kit for meeting brief."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📅 Upcoming: {meeting.title}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*When:* {format_time(meeting.start_time)}"},
                {"type": "mrkdwn", "text": f"*Duration:* {duration_str}"}
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Participants:*\n{attendee_list}"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Context Brief:*\n{brief.content}"}
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Confidence: {confidence_emoji(brief.confidence)}"}
            ]
        },
        {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "📝 Add Note"}, "action_id": "meeting_add_note", "value": str(meeting.id)},
                {"type": "button", "text": {"type": "plain_text", "text": "⏰ Snooze 10m"}, "action_id": "meeting_snooze", "value": str(meeting.id)},
                {"type": "button", "text": {"type": "plain_text", "text": "🔕 Skip Brief"}, "action_id": "meeting_skip", "value": str(meeting.id)}
            ]
        }
    ]
```

---

## Dependencies

### New Packages

| Package | Version | Purpose |
|---------|---------|---------|
| - | - | No new packages needed |

### External Services

| Service | Purpose | Config Needed |
|---------|---------|---------------|
| Google Calendar API | Fetch calendar events | OAuth scopes: calendar.readonly |
| Gmail API | Fetch email context | Already configured (FEAT-001) |
| Slack API | Send briefs | Already configured (FEAT-006) |

---

## Error Handling

| Error | HTTP Code | Response | Recovery |
|-------|-----------|----------|----------|
| Calendar not connected | 400 | `{"error": "Calendar not connected"}` | Redirect to OAuth |
| Calendar API rate limit | 429 | `{"error": "Rate limit exceeded"}` | Retry with backoff |
| Meeting not found | 404 | `{"error": "Meeting not found"}` | - |
| LLM timeout | 504 | `{"error": "Brief generation timeout"}` | Retry once |
| Auth expired | 401 | `{"error": "Calendar auth expired"}` | Re-auth flow |

---

## Security Considerations

- [x] Calendar OAuth scopes: only `calendar.readonly` (minimal)
- [x] Brief sent only to DM (never channels)
- [x] Email content summarized, not copied verbatim
- [x] Meeting data isolated by tenant_id
- [x] Rate limiting: 30 meetings/month per plan
- [x] Audit log of all brief generations

---

## Performance Considerations

| Aspect | Approach |
|--------|----------|
| Calendar sync | Batch fetch (7 days), incremental sync |
| Email context | Query last 5 emails per participant, cached |
| Brief generation | Claude Haiku for speed + cost |
| Concurrent syncs | Max 10 users per worker |

---

## Testing Strategy

| Type | Coverage Target | Tools |
|------|-----------------|-------|
| Unit | 80%+ | pytest, pytest-asyncio |
| Integration | Calendar sync, brief gen | pytest, mock Calendar API |
| E2E | Full flow | pytest, actual APIs (staging) |

---

## Implementation Order

1. **Phase 1: Foundation** (Tasks 1-4)
   - Database models and migration
   - Calendar client integration
   - Basic service structure

2. **Phase 2: Agent Core** (Tasks 5-9)
   - MeetingState definition
   - Agent graph nodes
   - Brief generation with LLM

3. **Phase 3: Notifications** (Tasks 10-12)
   - Slack blocks for briefs
   - Notification flow
   - Action handlers

4. **Phase 4: Scheduling** (Tasks 13-15)
   - Celery tasks
   - Beat schedule
   - Sync job

5. **Phase 5: API & Config** (Tasks 16-18)
   - REST endpoints
   - User config management

6. **Phase 6: Testing** (Tasks 19-22)
   - Unit tests
   - Integration tests

7. **Phase 7: Polish** (Tasks 23-25)
   - Error handling
   - Documentation
   - Audit logging

---

## Open Technical Questions

- [x] Calendar Watch API vs polling? → Start with polling, add webhook later
- [x] Email context caching? → Cache for 15 min, invalidate on sync
- [x] Brief template customization? → Not in MVP, future feature

---

## References

- [Google Calendar API](https://developers.google.com/calendar/api)
- [InboxPilot implementation](../FEAT-003-inbox-pilot/)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)

---

*Created: 2026-02-02*
*Last updated: 2026-02-02*
*Approved: [x] Approved by analysis.md (Medium-High confidence)*
