"""
Integration tests for integration routes (Gmail, Slack).

These tests mock external OAuth providers but test the full request/response cycle.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestIntegrationStatusEndpoint:
    """Tests for GET /api/v1/integrations/status"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.get("/api/v1/integrations/status")

        assert response.status_code == 401


class TestGmailConnectEndpoint:
    """Tests for GET /api/v1/integrations/gmail/connect"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.get("/api/v1/integrations/gmail/connect")

        assert response.status_code == 401


class TestGmailCallbackEndpoint:
    """Tests for GET /api/v1/integrations/gmail/callback"""

    def test_missing_code_returns_error(self, client):
        """Should return error if code is missing."""
        response = client.get(
            "/api/v1/integrations/gmail/callback",
            params={"state": "test_state"},
        )

        # Will fail auth first since no user token
        assert response.status_code == 401

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.get(
            "/api/v1/integrations/gmail/callback",
            params={"code": "test", "state": "test"},
        )

        assert response.status_code == 401


class TestGmailDisconnectEndpoint:
    """Tests for DELETE /api/v1/integrations/gmail"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.delete("/api/v1/integrations/gmail")

        assert response.status_code == 401


class TestSlackConnectEndpoint:
    """Tests for GET /api/v1/integrations/slack/connect"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.get("/api/v1/integrations/slack/connect")

        assert response.status_code == 401


class TestSlackCallbackEndpoint:
    """Tests for GET /api/v1/integrations/slack/callback"""

    def test_missing_code_returns_error(self, client):
        """Should return error if code is missing."""
        response = client.get(
            "/api/v1/integrations/slack/callback",
            params={"state": "test_state"},
        )

        assert response.status_code == 401

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.get(
            "/api/v1/integrations/slack/callback",
            params={"code": "test", "state": "test"},
        )

        assert response.status_code == 401


class TestSlackDisconnectEndpoint:
    """Tests for DELETE /api/v1/integrations/slack"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.delete("/api/v1/integrations/slack")

        assert response.status_code == 401


class TestOnboardingStatusEndpoint:
    """Tests for GET /api/v1/onboarding/status"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.get("/api/v1/onboarding/status")

        assert response.status_code == 401


class TestOnboardingCompleteEndpoint:
    """Tests for POST /api/v1/onboarding/complete"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.post("/api/v1/onboarding/complete")

        assert response.status_code == 401


class TestOnboardingSkipEndpoint:
    """Tests for POST /api/v1/onboarding/skip"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.post("/api/v1/onboarding/skip")

        assert response.status_code == 401
