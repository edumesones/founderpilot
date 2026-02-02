"""
End-to-end test for agent audit dashboard.

This test simulates a complete user workflow:
1. User authenticates
2. Creates audit log entries
3. Views logs in dashboard with filtering
4. Views log details
5. Checks statistics
6. Marks log as rolled back
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
def mock_audit_logs():
    """Create a collection of mock audit logs for testing."""
    from src.models.agent_audit_log import AgentAuditLog

    base_time = datetime.now(timezone.utc)
    user_id = uuid4()

    logs = []

    # High confidence inbox pilot log
    log1 = MagicMock(spec=AgentAuditLog)
    log1.id = uuid4()
    log1.timestamp = base_time - timedelta(hours=1)
    log1.user_id = user_id
    log1.workflow_id = uuid4()
    log1.agent_type = AgentType.INBOX_PILOT
    log1.action = InboxPilotAction.CLASSIFY_EMAIL
    log1.input_summary = "Urgent: Budget approval needed"
    log1.output_summary = "Classified as urgent, forwarded to finance team"
    log1.decision = "Auto-forward to finance@example.com"
    log1.confidence = 0.95
    log1.escalated = False
    log1.authorized_by = "agent"
    log1.trace_id = "trace_001"
    log1.metadata_ = {"subject": "Budget approval", "from": "ceo@example.com"}
    log1.rolled_back = False
    log1.created_at = base_time - timedelta(hours=1)
    log1.updated_at = base_time - timedelta(hours=1)
    logs.append(log1)

    # Low confidence escalated log
    log2 = MagicMock(spec=AgentAuditLog)
    log2.id = uuid4()
    log2.timestamp = base_time - timedelta(hours=2)
    log2.user_id = user_id
    log2.workflow_id = uuid4()
    log2.agent_type = AgentType.INBOX_PILOT
    log2.action = InboxPilotAction.CLASSIFY_EMAIL
    log2.input_summary = "Unclear request from unknown sender"
    log2.output_summary = "Unable to determine category confidently"
    log2.decision = "Escalate to user for review"
    log2.confidence = 0.45
    log2.escalated = True
    log2.authorized_by = "user"
    log2.trace_id = "trace_002"
    log2.metadata_ = {"subject": "Inquiry", "from": "unknown@example.com"}
    log2.rolled_back = False
    log2.created_at = base_time - timedelta(hours=2)
    log2.updated_at = base_time - timedelta(hours=2)
    logs.append(log2)

    # Invoice pilot log
    log3 = MagicMock(spec=AgentAuditLog)
    log3.id = uuid4()
    log3.timestamp = base_time - timedelta(hours=3)
    log3.user_id = user_id
    log3.workflow_id = uuid4()
    log3.agent_type = AgentType.INVOICE_PILOT
    log3.action = "process_invoice"
    log3.input_summary = "Invoice #12345 - $5,000 from Acme Corp"
    log3.output_summary = "Invoice approved and scheduled for payment"
    log3.decision = "Auto-approve within policy limits"
    log3.confidence = 0.88
    log3.escalated = False
    log3.authorized_by = "agent"
    log3.trace_id = "trace_003"
    log3.metadata_ = {"invoice_number": "12345", "amount": 5000}
    log3.rolled_back = False
    log3.created_at = base_time - timedelta(hours=3)
    log3.updated_at = base_time - timedelta(hours=3)
    logs.append(log3)

    return logs


@patch("src.api.dependencies.get_current_user")
@patch("src.api.routes.agent_audit.get_agent_audit_service")
class TestAuditDashboardE2E:
    """End-to-end tests for audit dashboard workflow."""

    def test_complete_audit_dashboard_workflow(
        self, mock_get_service, mock_get_user, client, mock_user, mock_audit_logs
    ):
        """
        Complete E2E test simulating a user workflow through the audit dashboard.

        Flow:
        1. User loads dashboard and sees all logs
        2. User filters to see only escalated logs
        3. User views details of escalated log
        4. User checks statistics
        5. User marks escalated log as rolled back
        6. User verifies the rollback
        """
        # Setup authentication
        mock_get_user.return_value = mock_user
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Step 1: Load dashboard - get all logs
        mock_service.get_logs.return_value = (mock_audit_logs, None, False)
        response = client.get("/api/v1/audit?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 3
        assert data["has_more"] is False

        # Verify logs are in chronological order (most recent first)
        entries = data["entries"]
        assert entries[0]["confidence"] == 0.95
        assert entries[1]["confidence"] == 0.45
        assert entries[2]["confidence"] == 0.88

        # Step 2: Filter to see only escalated logs
        escalated_log = mock_audit_logs[1]  # The low confidence escalated log
        mock_service.get_logs.return_value = ([escalated_log], None, False)

        response = client.get("/api/v1/audit?escalated=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["escalated"] is True
        assert data["entries"][0]["confidence"] == 0.45
        assert data["entries"][0]["authorized_by"] == "user"

        # Step 3: View details of escalated log
        mock_service.get_log_by_id.return_value = escalated_log

        response = client.get(f"/api/v1/audit/{escalated_log.id}")

        assert response.status_code == 200
        detail = response.json()
        assert detail["id"] == str(escalated_log.id)
        assert detail["escalated"] is True
        assert detail["input_summary"] == "Unclear request from unknown sender"
        assert detail["decision"] == "Escalate to user for review"
        assert "unknown@example.com" in str(detail["metadata"])

        # Step 4: Check statistics
        stats = {
            "total_actions": 3,
            "by_agent": {
                AgentType.INBOX_PILOT: 2,
                AgentType.INVOICE_PILOT: 1,
            },
            "escalated_count": 1,
            "escalation_rate": 0.33,
            "average_confidence": 0.76,  # (0.95 + 0.45 + 0.88) / 3
        }
        mock_service.get_stats.return_value = stats

        response = client.get("/api/v1/audit/stats/summary")

        assert response.status_code == 200
        stats_data = response.json()
        assert stats_data["total_actions"] == 3
        assert stats_data["escalated_count"] == 1
        assert stats_data["escalation_rate"] == 0.33
        assert abs(stats_data["average_confidence"] - 0.76) < 0.01

        # Step 5: Mark escalated log as rolled back
        escalated_log.rolled_back = True
        mock_service.mark_rolled_back.return_value = escalated_log

        response = client.post(f"/api/v1/audit/{escalated_log.id}/rollback")

        assert response.status_code == 200
        rollback_data = response.json()
        assert rollback_data["success"] is True
        assert rollback_data["log_id"] == str(escalated_log.id)

        # Step 6: Verify the rollback by viewing details again
        response = client.get(f"/api/v1/audit/{escalated_log.id}")

        assert response.status_code == 200
        detail = response.json()
        assert detail["rolled_back"] is True

    def test_pagination_workflow(
        self, mock_get_service, mock_get_user, client, mock_user, mock_audit_logs
    ):
        """
        Test pagination workflow through multiple pages.

        Simulates:
        1. First page with cursor
        2. Next page using cursor
        3. No more results
        """
        mock_get_user.return_value = mock_user
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Step 1: Get first page
        first_page = mock_audit_logs[:2]
        next_cursor = uuid4()
        mock_service.get_logs.return_value = (first_page, next_cursor, True)

        response = client.get("/api/v1/audit?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"] == str(next_cursor)

        # Step 2: Get next page using cursor
        second_page = mock_audit_logs[2:]
        mock_service.get_logs.return_value = (second_page, None, False)

        response = client.get(f"/api/v1/audit?limit=2&cursor={next_cursor}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    def test_filtering_workflow(
        self, mock_get_service, mock_get_user, client, mock_user, mock_audit_logs
    ):
        """
        Test complex filtering workflow.

        Simulates:
        1. Filter by agent type
        2. Filter by confidence
        3. Combine multiple filters
        4. Search by text
        """
        mock_get_user.return_value = mock_user
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Step 1: Filter by agent type (inbox_pilot only)
        inbox_logs = [log for log in mock_audit_logs if log.agent_type == AgentType.INBOX_PILOT]
        mock_service.get_logs.return_value = (inbox_logs, None, False)

        response = client.get("/api/v1/audit?agent=inbox_pilot")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert all(entry["agent_type"] == AgentType.INBOX_PILOT for entry in data["entries"])

        # Step 2: Filter by minimum confidence (high confidence only)
        high_confidence_logs = [log for log in mock_audit_logs if log.confidence >= 0.8]
        mock_service.get_logs.return_value = (high_confidence_logs, None, False)

        response = client.get("/api/v1/audit?min_confidence=0.8")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert all(entry["confidence"] >= 0.8 for entry in data["entries"])

        # Step 3: Combine filters (inbox_pilot + high confidence + non-escalated)
        filtered_logs = [
            log for log in mock_audit_logs
            if log.agent_type == AgentType.INBOX_PILOT
            and log.confidence >= 0.8
            and not log.escalated
        ]
        mock_service.get_logs.return_value = (filtered_logs, None, False)

        response = client.get("/api/v1/audit?agent=inbox_pilot&min_confidence=0.8&escalated=false")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["agent_type"] == AgentType.INBOX_PILOT
        assert data["entries"][0]["confidence"] >= 0.8
        assert data["entries"][0]["escalated"] is False

        # Step 4: Search by text
        search_results = [mock_audit_logs[0]]  # The budget approval log
        mock_service.get_logs.return_value = (search_results, None, False)

        response = client.get("/api/v1/audit?search=budget")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert "budget" in data["entries"][0]["input_summary"].lower()

    def test_error_handling_workflow(
        self, mock_get_service, mock_get_user, client, mock_user
    ):
        """
        Test error handling scenarios.

        Simulates:
        1. Non-existent log detail
        2. Invalid filter parameters
        3. Service errors
        """
        mock_get_user.return_value = mock_user
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        # Step 1: Try to get non-existent log
        mock_service.get_log_by_id.return_value = None
        non_existent_id = uuid4()

        response = client.get(f"/api/v1/audit/{non_existent_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

        # Step 2: Invalid confidence range
        response = client.get("/api/v1/audit?min_confidence=1.5")
        assert response.status_code == 422

        # Step 3: Invalid limit
        response = client.get("/api/v1/audit?limit=200")
        assert response.status_code == 422

        # Step 4: Try to rollback non-existent log
        mock_service.mark_rolled_back.return_value = None

        response = client.post(f"/api/v1/audit/{non_existent_id}/rollback")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
