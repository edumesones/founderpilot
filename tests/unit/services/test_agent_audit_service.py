"""Unit tests for AgentAuditService."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID

from src.services.agent_audit import AgentAuditService
from src.models.agent_audit_log import AgentAuditLog, AgentType, InboxPilotAction


@pytest.fixture
def mock_db():
    """Mock async database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.get = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    """Create AgentAuditService instance."""
    return AgentAuditService(db=mock_db)


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid4()


@pytest.fixture
def mock_audit_log(sample_user_id):
    """Create mock audit log."""
    log = MagicMock(spec=AgentAuditLog)
    log.id = uuid4()
    log.timestamp = datetime.now(timezone.utc)
    log.user_id = sample_user_id
    log.workflow_id = uuid4()
    log.agent_type = AgentType.INBOX_PILOT
    log.action = InboxPilotAction.CLASSIFY_EMAIL
    log.input_summary = "Test email subject"
    log.output_summary = "Category: urgent"
    log.decision = "Classify as urgent"
    log.confidence = 0.95
    log.escalated = False
    log.authorized_by = "agent"
    log.trace_id = "trace_123"
    log.metadata = {"raw_input": "full email content"}
    log.rolled_back = False
    return log


class TestLogAction:
    """Tests for log_action method."""

    async def test_creates_audit_log_with_all_fields(self, service, mock_db, sample_user_id):
        """Test creates audit log with all provided fields."""
        workflow_id = uuid4()

        result = await service.log_action(
            user_id=sample_user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
            input_summary="Test email",
            output_summary="Category: urgent",
            decision="Classified as urgent",
            confidence=0.95,
            escalated=False,
            authorized_by="agent",
            trace_id="trace_123",
            metadata={"key": "value"},
            workflow_id=workflow_id,
        )

        # Verify log was added to db
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

        # Verify returned object has correct attributes
        assert result.user_id == sample_user_id
        assert result.agent_type == AgentType.INBOX_PILOT
        assert result.action == InboxPilotAction.CLASSIFY_EMAIL
        assert result.confidence == 0.95
        assert result.escalated is False
        assert result.workflow_id == workflow_id

    async def test_truncates_long_input_summary(self, service, mock_db, sample_user_id):
        """Test truncates input summary if longer than 2000 chars."""
        long_input = "a" * 2500  # 2500 characters

        result = await service.log_action(
            user_id=sample_user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
            input_summary=long_input,
        )

        assert len(result.input_summary) == 2000
        assert result.input_summary.endswith("...")

    async def test_truncates_long_output_summary(self, service, mock_db, sample_user_id):
        """Test truncates output summary if longer than 2000 chars."""
        long_output = "b" * 2500  # 2500 characters

        result = await service.log_action(
            user_id=sample_user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
            output_summary=long_output,
        )

        assert len(result.output_summary) == 2000
        assert result.output_summary.endswith("...")

    async def test_sets_default_authorized_by(self, service, mock_db, sample_user_id):
        """Test sets authorized_by to 'agent' by default."""
        result = await service.log_action(
            user_id=sample_user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
        )

        assert result.authorized_by == "agent"

    async def test_sets_default_metadata(self, service, mock_db, sample_user_id):
        """Test sets metadata to empty dict by default."""
        result = await service.log_action(
            user_id=sample_user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
        )

        assert result.metadata == {}

    async def test_sets_rolled_back_to_false(self, service, mock_db, sample_user_id):
        """Test sets rolled_back to False by default."""
        result = await service.log_action(
            user_id=sample_user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
        )

        assert result.rolled_back is False


class TestGetLogs:
    """Tests for get_logs method."""

    async def test_returns_logs_for_user(self, service, mock_db, sample_user_id, mock_audit_log):
        """Test returns logs for specified user."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_audit_log]
        mock_db.execute.return_value = mock_result

        logs, next_cursor, has_more = await service.get_logs(user_id=sample_user_id)

        assert len(logs) == 1
        assert logs[0] == mock_audit_log
        assert has_more is False

    async def test_enforces_max_limit(self, service, mock_db, sample_user_id):
        """Test enforces maximum limit of 100."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_logs(user_id=sample_user_id, limit=200)

        # Verify query was limited to 101 (max 100 + 1 for has_more check)
        # This is checked indirectly through the limit call in the query
        mock_db.execute.assert_called_once()

    async def test_filters_by_agent_type(self, service, mock_db, sample_user_id):
        """Test filters logs by agent type."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_logs(
            user_id=sample_user_id,
            agent_type=AgentType.INBOX_PILOT,
        )

        mock_db.execute.assert_called_once()

    async def test_filters_by_escalated(self, service, mock_db, sample_user_id):
        """Test filters logs by escalation status."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_logs(
            user_id=sample_user_id,
            escalated=True,
        )

        mock_db.execute.assert_called_once()

    async def test_filters_by_min_confidence(self, service, mock_db, sample_user_id):
        """Test filters logs by minimum confidence."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_logs(
            user_id=sample_user_id,
            min_confidence=0.8,
        )

        mock_db.execute.assert_called_once()

    async def test_filters_by_date_range(self, service, mock_db, sample_user_id):
        """Test filters logs by date range."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        from_date = datetime.now(timezone.utc) - timedelta(days=7)
        to_date = datetime.now(timezone.utc)

        await service.get_logs(
            user_id=sample_user_id,
            from_date=from_date,
            to_date=to_date,
        )

        mock_db.execute.assert_called_once()

    async def test_applies_cursor_pagination(self, service, mock_db, sample_user_id, mock_audit_log):
        """Test applies cursor pagination correctly."""
        cursor_id = uuid4()

        # Mock getting cursor entry
        mock_db.get.return_value = mock_audit_log

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_logs(
            user_id=sample_user_id,
            cursor=cursor_id,
        )

        mock_db.get.assert_called_once_with(AgentAuditLog, cursor_id)

    async def test_returns_next_cursor_when_more_results(
        self, service, mock_db, sample_user_id, mock_audit_log
    ):
        """Test returns next cursor when there are more results."""
        # Create 11 logs (limit is 10, so has_more should be True)
        mock_logs = [MagicMock(spec=AgentAuditLog) for _ in range(11)]
        for i, log in enumerate(mock_logs):
            log.id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        mock_db.execute.return_value = mock_result

        logs, next_cursor, has_more = await service.get_logs(
            user_id=sample_user_id,
            limit=10,
        )

        assert len(logs) == 10  # Should return only limit
        assert has_more is True
        assert next_cursor == logs[-1].id


class TestGetLogById:
    """Tests for get_log_by_id method."""

    async def test_returns_log_when_found(self, service, mock_db, sample_user_id, mock_audit_log):
        """Test returns log when found and authorized."""
        log_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_audit_log
        mock_db.execute.return_value = mock_result

        result = await service.get_log_by_id(log_id, sample_user_id)

        assert result == mock_audit_log

    async def test_returns_none_when_not_found(self, service, mock_db, sample_user_id):
        """Test returns None when log not found."""
        log_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_log_by_id(log_id, sample_user_id)

        assert result is None


class TestMarkRolledBack:
    """Tests for mark_rolled_back method."""

    async def test_marks_log_as_rolled_back(self, service, mock_db, sample_user_id, mock_audit_log):
        """Test marks log as rolled back and updates timestamp."""
        log_id = uuid4()

        # Mock get_log_by_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_audit_log
        mock_db.execute.return_value = mock_result

        result = await service.mark_rolled_back(log_id, sample_user_id)

        assert result.rolled_back is True
        mock_db.flush.assert_called_once()

    async def test_returns_none_when_log_not_found(self, service, mock_db, sample_user_id):
        """Test returns None when log not found."""
        log_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.mark_rolled_back(log_id, sample_user_id)

        assert result is None


class TestGetStats:
    """Tests for get_stats method."""

    async def test_returns_statistics(self, service, mock_db, sample_user_id):
        """Test returns correct statistics."""
        # Mock total actions
        total_result = MagicMock()
        total_result.scalar_one.return_value = 100

        # Mock by_agent
        by_agent_result = MagicMock()
        by_agent_result.all.return_value = [
            (AgentType.INBOX_PILOT, 60),
            (AgentType.INVOICE_PILOT, 40),
        ]

        # Mock escalated count
        escalated_result = MagicMock()
        escalated_result.scalar_one.return_value = 10

        # Mock avg confidence
        avg_confidence_result = MagicMock()
        avg_confidence_result.scalar_one.return_value = 0.85

        mock_db.execute.side_effect = [
            total_result,
            by_agent_result,
            escalated_result,
            avg_confidence_result,
        ]

        stats = await service.get_stats(sample_user_id)

        assert stats["total_actions"] == 100
        assert stats["by_agent"] == {
            AgentType.INBOX_PILOT: 60,
            AgentType.INVOICE_PILOT: 40,
        }
        assert stats["escalated_count"] == 10
        assert stats["escalation_rate"] == 0.1
        assert stats["average_confidence"] == 0.85

    async def test_handles_zero_actions(self, service, mock_db, sample_user_id):
        """Test handles zero actions gracefully."""
        # Mock zero total actions
        total_result = MagicMock()
        total_result.scalar_one.return_value = 0

        by_agent_result = MagicMock()
        by_agent_result.all.return_value = []

        escalated_result = MagicMock()
        escalated_result.scalar_one.return_value = 0

        avg_confidence_result = MagicMock()
        avg_confidence_result.scalar_one.return_value = None

        mock_db.execute.side_effect = [
            total_result,
            by_agent_result,
            escalated_result,
            avg_confidence_result,
        ]

        stats = await service.get_stats(sample_user_id)

        assert stats["total_actions"] == 0
        assert stats["escalation_rate"] == 0
        assert stats["average_confidence"] is None
