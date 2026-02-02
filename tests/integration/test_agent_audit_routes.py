"""
Integration tests for agent audit routes.

These tests use the FastAPI TestClient to test the full request/response cycle
for the audit log endpoints.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from src.api.main import app
from src.models.agent_audit_log import AgentType, InboxPilotAction


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    from src.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_audit_log():
    """Mock audit log entry."""
    from src.models.agent_audit_log import AgentAuditLog

    log = MagicMock(spec=AgentAuditLog)
    log.id = uuid4()
    log.timestamp = datetime.now(timezone.utc)
    log.user_id = uuid4()
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
    log.created_at = datetime.now(timezone.utc)
    log.updated_at = datetime.now(timezone.utc)
    return log


class TestGetAuditLogs:
    """Tests for GET /api/v1/audit"""

    def test_unauthenticated_returns_401(self, client):
        """Should return 401 if not authenticated."""
        response = client.get("/api/v1/audit")
        assert response.status_code == 401

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_returns_empty_list_when_no_logs(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should return empty list when user has no logs."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.get_logs.return_value = ([], None, False)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/audit")

        assert response.status_code == 200
        data = response.json()
        assert data["entries"] == []
        assert data["next_cursor"] is None
        assert data["has_more"] is False

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_returns_logs_with_pagination(
        self, mock_get_user, mock_get_service, client, mock_user, mock_audit_log
    ):
        """Should return logs with pagination info."""
        mock_get_user.return_value = mock_user

        next_cursor = uuid4()
        mock_service = AsyncMock()
        mock_service.get_logs.return_value = ([mock_audit_log], next_cursor, True)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/audit?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["next_cursor"] == str(next_cursor)
        assert data["has_more"] is True

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_filters_by_agent_type(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should filter logs by agent type."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.get_logs.return_value = ([], None, False)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/audit?agent=inbox_pilot")

        assert response.status_code == 200
        mock_service.get_logs.assert_called_once()
        call_kwargs = mock_service.get_logs.call_args.kwargs
        assert call_kwargs["agent_type"] == "inbox_pilot"

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_filters_by_escalated(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should filter logs by escalation status."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.get_logs.return_value = ([], None, False)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/audit?escalated=true")

        assert response.status_code == 200
        mock_service.get_logs.assert_called_once()
        call_kwargs = mock_service.get_logs.call_args.kwargs
        assert call_kwargs["escalated"] is True

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_filters_by_min_confidence(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should filter logs by minimum confidence."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.get_logs.return_value = ([], None, False)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/audit?min_confidence=0.8")

        assert response.status_code == 200
        mock_service.get_logs.assert_called_once()
        call_kwargs = mock_service.get_logs.call_args.kwargs
        assert call_kwargs["min_confidence"] == 0.8

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_filters_by_date_range(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should filter logs by date range."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.get_logs.return_value = ([], None, False)
        mock_get_service.return_value = mock_service

        from_date = datetime.now(timezone.utc) - timedelta(days=7)
        to_date = datetime.now(timezone.utc)

        response = client.get(
            f"/api/v1/audit?from={from_date.isoformat()}&to={to_date.isoformat()}"
        )

        assert response.status_code == 200
        mock_service.get_logs.assert_called_once()

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_applies_search_query(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should apply search query to logs."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.get_logs.return_value = ([], None, False)
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/audit?search=urgent")

        assert response.status_code == 200
        mock_service.get_logs.assert_called_once()
        call_kwargs = mock_service.get_logs.call_args.kwargs
        assert call_kwargs["search"] == "urgent"

    def test_validates_limit_range(self, client, mock_user):
        """Should validate limit is within allowed range."""
        # Test limit too low
        response = client.get("/api/v1/audit?limit=0")
        assert response.status_code == 422

        # Test limit too high
        response = client.get("/api/v1/audit?limit=101")
        assert response.status_code == 422

    def test_validates_confidence_range(self, client, mock_user):
        """Should validate confidence is between 0 and 1."""
        # Test confidence too low
        response = client.get("/api/v1/audit?min_confidence=-0.1")
        assert response.status_code == 422

        # Test confidence too high
        response = client.get("/api/v1/audit?min_confidence=1.1")
        assert response.status_code == 422


class TestGetAuditLogDetail:
    """Tests for GET /api/v1/audit/{log_id}"""

    def test_unauthenticated_returns_401(self, client):
        """Should return 401 if not authenticated."""
        log_id = uuid4()
        response = client.get(f"/api/v1/audit/{log_id}")
        assert response.status_code == 401

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_returns_log_detail_when_found(
        self, mock_get_user, mock_get_service, client, mock_user, mock_audit_log
    ):
        """Should return log detail when found."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.get_log_by_id.return_value = mock_audit_log
        mock_get_service.return_value = mock_service

        response = client.get(f"/api/v1/audit/{mock_audit_log.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(mock_audit_log.id)

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_returns_404_when_not_found(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should return 404 when log not found."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.get_log_by_id.return_value = None
        mock_get_service.return_value = mock_service

        log_id = uuid4()
        response = client.get(f"/api/v1/audit/{log_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetAuditStats:
    """Tests for GET /api/v1/audit/stats/summary"""

    def test_unauthenticated_returns_401(self, client):
        """Should return 401 if not authenticated."""
        response = client.get("/api/v1/audit/stats/summary")
        assert response.status_code == 401

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_returns_stats(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should return stats for user."""
        mock_get_user.return_value = mock_user

        stats = {
            "total_actions": 100,
            "by_agent": {
                AgentType.INBOX_PILOT: 60,
                AgentType.INVOICE_PILOT: 40,
            },
            "escalated_count": 10,
            "escalation_rate": 0.1,
            "average_confidence": 0.85,
        }

        mock_service = AsyncMock()
        mock_service.get_stats.return_value = stats
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/audit/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_actions"] == 100
        assert data["escalated_count"] == 10
        assert data["escalation_rate"] == 0.1
        assert data["average_confidence"] == 0.85

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_handles_zero_actions(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should handle zero actions gracefully."""
        mock_get_user.return_value = mock_user

        stats = {
            "total_actions": 0,
            "by_agent": {},
            "escalated_count": 0,
            "escalation_rate": 0,
            "average_confidence": None,
        }

        mock_service = AsyncMock()
        mock_service.get_stats.return_value = stats
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/audit/stats/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_actions"] == 0
        assert data["escalation_rate"] == 0


class TestRollbackAuditLog:
    """Tests for POST /api/v1/audit/{log_id}/rollback"""

    def test_unauthenticated_returns_401(self, client):
        """Should return 401 if not authenticated."""
        log_id = uuid4()
        response = client.post(f"/api/v1/audit/{log_id}/rollback")
        assert response.status_code == 401

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_marks_log_as_rolled_back(
        self, mock_get_user, mock_get_service, client, mock_user, mock_audit_log
    ):
        """Should mark log as rolled back."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.mark_rolled_back.return_value = mock_audit_log
        mock_get_service.return_value = mock_service

        response = client.post(f"/api/v1/audit/{mock_audit_log.id}/rollback")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["log_id"] == str(mock_audit_log.id)

    @patch("src.api.routes.agent_audit.get_agent_audit_service")
    @patch("src.api.dependencies.get_current_user")
    def test_returns_404_when_not_found(
        self, mock_get_user, mock_get_service, client, mock_user
    ):
        """Should return 404 when log not found."""
        mock_get_user.return_value = mock_user

        mock_service = AsyncMock()
        mock_service.mark_rolled_back.return_value = None
        mock_get_service.return_value = mock_service

        log_id = uuid4()
        response = client.post(f"/api/v1/audit/{log_id}/rollback")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
