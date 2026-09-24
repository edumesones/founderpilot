# FEAT-006: Technical Design

## Overview

This design implements Slack integration for FounderPilot using Slack Bolt (Python SDK). The integration provides OAuth-based installation, secure token storage, rich notifications via Block Kit, and interactive button handlers for approving/rejecting agent actions.

---

## Architecture

### Component Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Slack API      │────▶│  Slack Bot      │────▶│  FastAPI        │
│  (External)     │◀────│  (Bolt App)     │◀────│  (API Routes)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │                        │
                                ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  SlackService   │────▶│  PostgreSQL     │
                        │  (Business)     │     │  (Tokens, Logs) │
                        └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Celery Worker  │
                        │  (Async Tasks)  │
                        └─────────────────┘
```

### Data Flow

```
1. OAuth Flow:
   User → Dashboard → /slack/install → Slack OAuth → /slack/callback → Store tokens → Welcome DM

2. Send Notification:
   Agent → SlackService.send_notification() → Celery task → Bolt app → Slack API → User DM

3. Handle Action:
   User clicks button → Slack → /webhooks/slack/interactive → Bolt handler →
   → Update workflow → Update message → Audit log
```

---

## File Structure

### New Files to Create

```
src/
├── integrations/
│   └── slack/
│       ├── __init__.py
│       ├── app.py              # Slack Bolt app initialization
│       ├── handlers.py         # Interactive component handlers
│       ├── blocks.py           # Block Kit message templates
│       └── oauth.py            # OAuth installation store
│
├── models/
│   └── slack_installation.py   # SQLAlchemy model
│
├── schemas/
│   └── slack.py                # Pydantic schemas
│
├── services/
│   └── slack_service.py        # High-level Slack operations
│
├── api/
│   └── routes/
│       └── slack.py            # API endpoints
│
└── workers/
    └── tasks/
        └── slack_tasks.py      # Celery tasks

tests/
├── unit/
│   ├── test_slack_service.py
│   └── test_slack_blocks.py
└── integration/
    └── test_slack_api.py

alembic/
└── versions/
    └── xxxx_add_slack_installations.py
```

### Files to Modify

| File | Changes |
|------|---------|
| `src/api/main.py` | Add Slack router import |
| `src/core/config.py` | Add Slack settings |
| `requirements.txt` | Add slack-bolt, cryptography |
| `.env.example` | Add SLACK_* variables |

---

## Data Model

### slack_installations Table

```python
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base
import uuid

class SlackInstallation(Base):
    __tablename__ = "slack_installations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Slack identifiers
    team_id = Column(String(32), nullable=False, index=True)
    team_name = Column(String(255))
    enterprise_id = Column(String(32), nullable=True)  # For Enterprise Grid

    # Bot info
    bot_user_id = Column(String(32), nullable=False)
    bot_access_token = Column(Text, nullable=False)  # Encrypted

    # User token (optional, for user-level actions)
    user_access_token = Column(Text, nullable=True)  # Encrypted
    user_slack_id = Column(String(32), nullable=True)

    # DM channel for notifications
    dm_channel_id = Column(String(32), nullable=True)

    # Metadata
    scopes = Column(Text)  # Comma-separated
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="slack_installation")
```

### Database Migration

```python
# alembic/versions/xxxx_add_slack_installations.py

def upgrade():
    op.create_table(
        'slack_installations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('team_id', sa.String(32), nullable=False),
        sa.Column('team_name', sa.String(255)),
        sa.Column('enterprise_id', sa.String(32)),
        sa.Column('bot_user_id', sa.String(32), nullable=False),
        sa.Column('bot_access_token', sa.Text, nullable=False),
        sa.Column('user_access_token', sa.Text),
        sa.Column('user_slack_id', sa.String(32)),
        sa.Column('dm_channel_id', sa.String(32)),
        sa.Column('scopes', sa.Text),
        sa.Column('installed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean, default=True),
    )
    op.create_index('ix_slack_installations_user_id', 'slack_installations', ['user_id'])
    op.create_index('ix_slack_installations_team_id', 'slack_installations', ['team_id'])

def downgrade():
    op.drop_table('slack_installations')
```

---

## API Design

### Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/integrations/slack/install` | Start OAuth flow | JWT |
| GET | `/api/v1/integrations/slack/callback` | OAuth callback | State token |
| POST | `/api/v1/webhooks/slack/events` | Event subscriptions | Slack signing |
| POST | `/api/v1/webhooks/slack/interactive` | Button/modal actions | Slack signing |
| GET | `/api/v1/integrations/slack/status` | Check connection | JWT |
| DELETE | `/api/v1/integrations/slack` | Disconnect | JWT |

### Request/Response Examples

```python
# GET /api/v1/integrations/slack/install
# Response: Redirect to Slack OAuth

# GET /api/v1/integrations/slack/callback?code=xxx&state=yyy
# Response 200
{
  "status": "connected",
  "team_name": "My Workspace",
  "bot_user_id": "U1234567890"
}

# GET /api/v1/integrations/slack/status
# Response 200
{
  "connected": true,
  "team_name": "My Workspace",
  "team_id": "T1234567890",
  "installed_at": "2026-01-31T10:00:00Z"
}

# DELETE /api/v1/integrations/slack
# Response 204 No Content
```

---

## Service Layer

### SlackService

```python
class SlackService:
    """High-level Slack operations for agents to use."""

    def __init__(self, db: Session, encryption_key: str):
        self.db = db
        self.cipher = Fernet(encryption_key)

    async def send_notification(
        self,
        user_id: UUID,
        notification_type: str,
        payload: NotificationPayload
    ) -> str:
        """
        Send a notification to user's Slack DM.
        Returns the message timestamp (ts) for later updates.
        """
        installation = await self.get_installation(user_id)
        if not installation:
            raise SlackNotConnectedError(user_id)

        blocks = self._build_blocks(notification_type, payload)

        # Queue as Celery task for reliability
        result = send_slack_message.delay(
            channel=installation.dm_channel_id,
            blocks=blocks,
            token=self._decrypt(installation.bot_access_token)
        )
        return result.id

    async def update_message(
        self,
        user_id: UUID,
        message_ts: str,
        new_blocks: list
    ) -> bool:
        """Update an existing message (e.g., after user action)."""
        pass

    async def get_installation(self, user_id: UUID) -> Optional[SlackInstallation]:
        """Get user's Slack installation if exists and active."""
        pass

    async def handle_oauth_callback(
        self,
        code: str,
        state: str,
        user_id: UUID
    ) -> SlackInstallation:
        """Complete OAuth flow and store tokens."""
        pass

    async def disconnect(self, user_id: UUID) -> bool:
        """Revoke tokens and mark as inactive."""
        pass

    def _encrypt(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        return self.cipher.decrypt(value.encode()).decode()

    def _build_blocks(self, notification_type: str, payload: NotificationPayload) -> list:
        """Build Block Kit blocks based on notification type."""
        pass
```

---

## Slack Bolt App

### App Initialization

```python
# src/integrations/slack/app.py
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.core.config import settings

# Initialize with token from env
app = App(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
)

# For OAuth installations (multi-tenant)
from slack_bolt.oauth.oauth_settings import OAuthSettings
from src.integrations.slack.oauth import PostgresInstallationStore

oauth_settings = OAuthSettings(
    client_id=settings.SLACK_CLIENT_ID,
    client_secret=settings.SLACK_CLIENT_SECRET,
    scopes=["chat:write", "users:read", "im:write", "im:history"],
    installation_store=PostgresInstallationStore(),
)

app = App(
    signing_secret=settings.SLACK_SIGNING_SECRET,
    oauth_settings=oauth_settings,
)
```

### Action Handlers

```python
# src/integrations/slack/handlers.py
from slack_bolt import Ack, Respond
from src.services.workflow_service import WorkflowService

@app.action("approve_action")
async def handle_approve(ack: Ack, body: dict, respond: Respond):
    """Handle Approve button click."""
    await ack()  # Acknowledge within 3 seconds

    workflow_id = body["actions"][0]["value"]
    user_slack_id = body["user"]["id"]

    # Process the approval
    workflow_service = WorkflowService()
    result = await workflow_service.approve(
        workflow_id=workflow_id,
        approved_by=user_slack_id
    )

    if result.success:
        # Update the original message
        await respond(
            replace_original=True,
            blocks=build_success_blocks(result)
        )
    else:
        await respond(
            response_type="ephemeral",
            text=f"Error: {result.error}"
        )

@app.action("reject_action")
async def handle_reject(ack: Ack, body: dict, respond: Respond):
    """Handle Reject button click."""
    await ack()
    # Similar to approve...

@app.action("edit_action")
async def handle_edit(ack: Ack, body: dict, client):
    """Open edit modal."""
    await ack()

    workflow_id = body["actions"][0]["value"]
    workflow = await WorkflowService().get(workflow_id)

    await client.views_open(
        trigger_id=body["trigger_id"],
        view=build_edit_modal(workflow)
    )

@app.view("edit_modal_submit")
async def handle_edit_submit(ack: Ack, body: dict, client):
    """Handle edit modal submission."""
    await ack()

    values = body["view"]["state"]["values"]
    edited_content = values["edit_block"]["edit_input"]["value"]
    workflow_id = body["view"]["private_metadata"]

    result = await WorkflowService().update_and_approve(
        workflow_id=workflow_id,
        new_content=edited_content
    )
    # Update original message...

@app.action("snooze_action")
async def handle_snooze(ack: Ack, body: dict, respond: Respond):
    """Snooze for later."""
    await ack()
    # Schedule reminder...
```

---

## Block Kit Templates

### Notification Blocks

```python
# src/integrations/slack/blocks.py

def build_email_notification(payload: EmailNotificationPayload) -> list:
    """Build blocks for email action notification."""
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📧 Email Action Required", "emoji": True}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*From:* {payload.sender}"},
                {"type": "mrkdwn", "text": f"*Subject:* {payload.subject}"}
            ]
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Classification: *{payload.classification}* ({payload.confidence}% confidence)"}
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Proposed Response:*\n```{payload.proposed_response[:500]}```"}
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve", "emoji": True},
                    "style": "primary",
                    "action_id": "approve_action",
                    "value": str(payload.workflow_id)
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Edit", "emoji": True},
                    "action_id": "edit_action",
                    "value": str(payload.workflow_id)
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Snooze", "emoji": True},
                    "action_id": "snooze_action",
                    "value": str(payload.workflow_id)
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject", "emoji": True},
                    "style": "danger",
                    "action_id": "reject_action",
                    "value": str(payload.workflow_id)
                }
            ]
        }
    ]

def build_success_blocks(result) -> list:
    """Build blocks for action confirmation."""
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"✅ *Action completed*\n{result.summary}"}
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Processed at {result.timestamp}"}
            ]
        }
    ]

def build_edit_modal(workflow) -> dict:
    """Build modal for editing proposed response."""
    return {
        "type": "modal",
        "callback_id": "edit_modal_submit",
        "private_metadata": str(workflow.id),
        "title": {"type": "plain_text", "text": "Edit Response"},
        "submit": {"type": "plain_text", "text": "Send"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "edit_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "edit_input",
                    "multiline": True,
                    "initial_value": workflow.proposed_response
                },
                "label": {"type": "plain_text", "text": "Response"}
            }
        ]
    }
```

---

## Dependencies

### New Packages

| Package | Version | Purpose |
|---------|---------|---------|
| slack-bolt | ^1.18.0 | Official Slack SDK |
| slack-sdk | ^3.23.0 | Slack API client (dependency of bolt) |
| cryptography | ^41.0.0 | Token encryption (Fernet) |

### Environment Variables

```bash
# .env.example
SLACK_CLIENT_ID=your-client-id
SLACK_CLIENT_SECRET=your-client-secret
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_BOT_TOKEN=xoxb-your-bot-token  # For dev/testing
SLACK_APP_TOKEN=xapp-your-app-token  # For Socket Mode
ENCRYPTION_KEY=your-32-byte-key-base64  # Fernet key
```

---

## Error Handling

| Error | HTTP Code | Response |
|-------|-----------|----------|
| Slack not connected | 400 | `{"error": "Slack not connected. Please install the app."}` |
| Invalid OAuth state | 400 | `{"error": "Invalid OAuth state. Please try again."}` |
| Token refresh failed | 500 | `{"error": "Failed to refresh Slack token"}` |
| Rate limited | 429 | `{"error": "Rate limited", "retry_after": 30}` |
| Workflow not found | 404 | `{"error": "Workflow not found"}` |
| Already processed | 409 | `{"error": "Action already processed"}` |

---

## Security Considerations

- [x] Input validation on all endpoints
- [x] Slack signing secret verification on webhooks
- [x] Token encryption at rest (Fernet/AES)
- [x] OAuth state parameter to prevent CSRF
- [x] Minimal scopes requested
- [x] Tokens never logged

---

## Testing Strategy

| Type | Coverage Target | Tools |
|------|-----------------|-------|
| Unit | 80%+ | pytest, pytest-asyncio |
| Integration | OAuth flow, message send | pytest, responses (mock HTTP) |
| E2E | Install → Notify → Action | Manual + Slack test workspace |

### Test Cases

1. **OAuth Flow**
   - Successful installation
   - Invalid state token
   - User cancels OAuth

2. **Token Management**
   - Encrypt/decrypt roundtrip
   - Token refresh on expiry

3. **Notifications**
   - Build correct blocks
   - Handle Slack API errors
   - Retry on failure

4. **Actions**
   - Approve updates workflow
   - Reject updates workflow
   - Edit opens modal, submit updates
   - Double-click is idempotent

---

## Implementation Order

1. **Phase 1: Foundation**
   - Create database model and migration
   - Add config settings
   - Set up basic Slack Bolt app

2. **Phase 2: OAuth**
   - Implement OAuth installation flow
   - Create token storage with encryption
   - Add status/disconnect endpoints

3. **Phase 3: Notifications**
   - Build Block Kit templates
   - Implement SlackService.send_notification()
   - Add Celery task for async sending

4. **Phase 4: Interactivity**
   - Implement action handlers
   - Add modal for editing
   - Connect to workflow service

5. **Phase 5: Testing**
   - Unit tests for all components
   - Integration tests for OAuth
   - Manual E2E testing

---

## Open Technical Questions

- [x] Socket Mode vs HTTP for webhooks? → **Socket Mode for dev, HTTP for prod**
- [x] Token encryption method? → **Fernet (symmetric AES)**
- [x] Where to run Bolt app? → **Same process as FastAPI via lifespan**

---

## References

- [Slack Bolt Python](https://slack.dev/bolt-python/concepts)
- [Block Kit Builder](https://app.slack.com/block-kit-builder)
- [Slack OAuth v2](https://api.slack.com/authentication/oauth-v2)
- [Slack Rate Limits](https://api.slack.com/docs/rate-limits)

---

*Created: 2026-01-31*
*Last updated: 2026-01-31*
*Approved: [x] Ready for implementation*
