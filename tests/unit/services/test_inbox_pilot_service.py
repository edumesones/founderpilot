"""Unit tests for InboxPilotService."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.inbox_pilot.service import InboxPilotService
from src.models.inbox_pilot.agent_config import InboxPilotConfig
from src.models.inbox_pilot.email_record import EmailRecord
from src.models.user import User


@pytest.fixture
def mock_db():
    """Mock async database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_llm_router():
    """Mock LLM router."""
    return MagicMock()


@pytest.fixture
def service(mock_db, mock_llm_router):
    """Create InboxPilotService instance."""
    return InboxPilotService(db=mock_db, llm_router=mock_llm_router)


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.google_access_token = "access_token"
    user.google_refresh_token = "refresh_token"
    user.google_token_expires_at = datetime.utcnow()
    return user


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = MagicMock(spec=InboxPilotConfig)
    config.user_id = uuid4()
    config.is_active = True
    config.escalation_threshold = 0.8
    config.draft_threshold = 0.7
    config.total_emails_processed = 0
    config.total_escalations = 0
    config.total_drafts_sent = 0
    return config


class TestGetOrCreateConfig:
    """Tests for get_or_create_config method."""

    async def test_returns_existing_config(self, service, mock_db, mock_config):
        """Test returns existing config when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_db.execute.return_value = mock_result

        result = await service.get_or_create_config(mock_config.user_id)

        assert result == mock_config
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    async def test_creates_new_config_when_not_found(self, service, mock_db):
        """Test creates new config when none exists."""
        user_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock the refresh to set the returned config
        async def mock_refresh(obj):
            obj.id = uuid4()
        mock_db.refresh.side_effect = mock_refresh

        result = await service.get_or_create_config(user_id)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.user_id == user_id


class TestUpdateConfig:
    """Tests for update_config method."""

    async def test_updates_config_fields(self, service, mock_db, mock_config):
        """Test updates config with provided fields."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_db.execute.return_value = mock_result

        from src.schemas.inbox_pilot.config import InboxPilotConfigUpdate
        updates = InboxPilotConfigUpdate(
            escalation_threshold=0.9,
            draft_threshold=0.6,
        )

        result = await service.update_config(mock_config.user_id, updates)

        assert result.escalation_threshold == 0.9
        assert result.draft_threshold == 0.6
        mock_db.commit.assert_called()


class TestListEmails:
    """Tests for list_emails method."""

    async def test_returns_paginated_results(self, service, mock_db):
        """Test returns paginated email list."""
        user_id = uuid4()

        # Mock count query
        count_result = MagicMock()
        count_result.all.return_value = [1, 2, 3]  # 3 items

        # Mock records query
        records_result = MagicMock()
        mock_records = [MagicMock(spec=EmailRecord) for _ in range(3)]
        records_result.scalars.return_value.all.return_value = mock_records

        mock_db.execute.side_effect = [count_result, records_result]

        records, total = await service.list_emails(user_id, page=1, limit=20)

        assert len(records) == 3
        assert total == 3

    async def test_filters_by_status(self, service, mock_db):
        """Test filters by status when provided."""
        user_id = uuid4()

        count_result = MagicMock()
        count_result.all.return_value = [1]

        records_result = MagicMock()
        records_result.scalars.return_value.all.return_value = [MagicMock(spec=EmailRecord)]

        mock_db.execute.side_effect = [count_result, records_result]

        await service.list_emails(user_id, status="escalated")

        # Verify execute was called (status filter applied)
        assert mock_db.execute.call_count == 2

    async def test_filters_by_category(self, service, mock_db):
        """Test filters by category when provided."""
        user_id = uuid4()

        count_result = MagicMock()
        count_result.all.return_value = [1, 2]

        records_result = MagicMock()
        records_result.scalars.return_value.all.return_value = [
            MagicMock(spec=EmailRecord),
            MagicMock(spec=EmailRecord),
        ]

        mock_db.execute.side_effect = [count_result, records_result]

        records, total = await service.list_emails(user_id, category="urgent")

        assert total == 2


class TestGetEmail:
    """Tests for get_email method."""

    async def test_returns_email_when_found(self, service, mock_db):
        """Test returns email record when found."""
        email_id = uuid4()
        mock_record = MagicMock(spec=EmailRecord)
        mock_record.id = email_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_record
        mock_db.execute.return_value = mock_result

        result = await service.get_email(email_id)

        assert result == mock_record

    async def test_returns_none_when_not_found(self, service, mock_db):
        """Test returns None when email not found."""
        email_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_email(email_id)

        assert result is None


class TestIdempotency:
    """Tests for idempotency in process_email."""

    async def test_returns_existing_record_for_duplicate_message(
        self, service, mock_db
    ):
        """Test returns existing record when message already processed."""
        message_id = "msg_123"
        existing_record = MagicMock(spec=EmailRecord)
        existing_record.gmail_message_id = message_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_record
        mock_db.execute.return_value = mock_result

        result = await service.process_email(uuid4(), message_id)

        assert result == existing_record
        # Should not have added a new record
        mock_db.add.assert_not_called()


class TestProcessEmailValidation:
    """Tests for process_email validation."""

    async def test_raises_when_agent_paused(
        self, service, mock_db, mock_user, mock_config
    ):
        """Test raises error when agent is paused."""
        mock_config.is_active = False

        # First call returns None (no existing record)
        # Second call returns user
        # Third call returns config
        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_config)),
        ]
        mock_db.execute.side_effect = mock_results

        with pytest.raises(ValueError, match="InboxPilot is paused"):
            await service.process_email(mock_user.id, "msg_new")

    async def test_raises_when_user_not_found(self, service, mock_db):
        """Test raises error when user not found."""
        user_id = uuid4()

        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # No existing record
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # No user found
        ]
        mock_db.execute.side_effect = mock_results

        with pytest.raises(ValueError, match="User not found"):
            await service.process_email(user_id, "msg_new")


class TestHandleSlackAction:
    """Tests for handle_slack_action method."""

    async def test_raises_when_email_not_found(self, service, mock_db):
        """Test raises error when email record not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Email record not found"):
            await service.handle_slack_action("msg_missing", "approve")
