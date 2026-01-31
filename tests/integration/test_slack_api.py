"""Integration tests for Slack API endpoints."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from uuid import UUID

from src.api.main import app
from src.services.slack_service import SlackService
from src.schemas.slack import SlackStatusResponse


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_current_user():
    """Mock authenticated user."""
    return UUID("12345678-1234-5678-1234-567812345678")


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "slack_configured" in data


class TestSlackStatusEndpoint:
    """Tests for Slack status endpoint."""

    def test_status_not_connected(self, client):
        """Test status when Slack is not connected."""
        with patch("src.api.routes.slack.get_slack_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_status.return_value = SlackStatusResponse(connected=False)
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/integrations/slack/status")

        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False

    def test_status_connected(self, client):
        """Test status when Slack is connected."""
        from datetime import datetime

        with patch("src.api.routes.slack.get_slack_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.get_status.return_value = SlackStatusResponse(
                connected=True,
                team_name="Test Workspace",
                team_id="T12345",
                installed_at=datetime.utcnow(),
            )
            mock_service.return_value = mock_instance

            response = client.get("/api/v1/integrations/slack/status")

        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["team_name"] == "Test Workspace"


class TestSlackDisconnectEndpoint:
    """Tests for Slack disconnect endpoint."""

    def test_disconnect_success(self, client):
        """Test successful disconnection."""
        with patch("src.api.routes.slack.get_slack_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.disconnect.return_value = True
            mock_service.return_value = mock_instance

            response = client.delete("/api/v1/integrations/slack")

        assert response.status_code == 204

    def test_disconnect_not_found(self, client):
        """Test disconnection when no connection exists."""
        with patch("src.api.routes.slack.get_slack_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.disconnect.return_value = False
            mock_service.return_value = mock_instance

            response = client.delete("/api/v1/integrations/slack")

        assert response.status_code == 404


class TestSlackInstallEndpoint:
    """Tests for Slack install endpoint."""

    def test_install_redirects_to_slack(self, client):
        """Test that install endpoint redirects to Slack OAuth."""
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.slack_configured = True
            mock_settings.SLACK_CLIENT_ID = "test-client-id"
            mock_settings.SLACK_REDIRECT_URI = "http://localhost/callback"
            mock_settings.FRONTEND_URL = "http://localhost:3000"

            response = client.get(
                "/api/v1/integrations/slack/install",
                follow_redirects=False,
            )

        assert response.status_code == 307
        assert "slack.com/oauth" in response.headers["location"]

    def test_install_returns_503_when_not_configured(self, client):
        """Test that install returns 503 when Slack not configured."""
        with patch("src.core.config.settings") as mock_settings:
            mock_settings.slack_configured = False

            response = client.get("/api/v1/integrations/slack/install")

        assert response.status_code == 503


class TestSlackWebhookEndpoints:
    """Tests for Slack webhook endpoints."""

    def test_events_url_verification(self, client):
        """Test Slack URL verification challenge."""
        # Skip signature verification for test
        with patch("src.api.routes.slack.verify_slack_signature", return_value=True):
            response = client.post(
                "/api/v1/integrations/slack/webhooks/events",
                json={
                    "type": "url_verification",
                    "challenge": "test-challenge-token",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == "test-challenge-token"

    def test_events_returns_ok(self, client):
        """Test that events endpoint acknowledges events."""
        with patch("src.api.routes.slack.verify_slack_signature", return_value=True):
            response = client.post(
                "/api/v1/integrations/slack/webhooks/events",
                json={
                    "type": "event_callback",
                    "event": {"type": "message"},
                },
            )

        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_events_rejects_invalid_signature(self, client):
        """Test that events endpoint rejects invalid signatures."""
        with patch("src.api.routes.slack.verify_slack_signature", return_value=False):
            response = client.post(
                "/api/v1/integrations/slack/webhooks/events",
                json={"type": "event_callback"},
            )

        assert response.status_code == 401
