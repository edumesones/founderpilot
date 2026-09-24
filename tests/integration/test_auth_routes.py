"""
Integration tests for auth routes.

These tests mock external OAuth providers but test the full request/response cycle.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

# One TestClient for the module: a new one per test strands event loops.
# follow_redirects=False because /auth/google answers with a 302 to Google,
# and following it would take the client off the app under test.
_client = TestClient(app, follow_redirects=False)


@pytest.fixture
def client(override_async_db):
    """Test client backed by the test database."""
    yield _client


@pytest.fixture
def mock_google_user_info():
    """Mock Google user info response."""
    return {
        "id": "google123",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/picture.jpg",
    }


class TestGoogleAuthEndpoint:
    """Tests for GET /api/v1/auth/google"""

    def test_redirects_to_google(self, client):
        """Should redirect to Google's authorization page."""
        response = client.get("/api/v1/auth/google")

        assert response.status_code == 302
        location = response.headers["location"]
        assert "accounts.google.com" in location
        assert "client_id=" in location
        assert "code_challenge=" in location  # PKCE

    def test_sets_oauth_state_cookie(self, client):
        """Should set the CSRF state cookie alongside the redirect."""
        response = client.get("/api/v1/auth/google")

        assert response.status_code == 302
        assert "oauth_state" in response.cookies

    def test_includes_required_scopes(self, client):
        """Should include email and profile scopes."""
        response = client.get("/api/v1/auth/google")

        location = response.headers["location"]
        assert "email" in location
        assert "profile" in location


class TestGoogleCallbackEndpoint:
    """Tests for GET /api/v1/auth/google/callback"""

    def test_missing_code_returns_error(self, client):
        """Should reject a callback without an authorization code.

        `code` is a required query parameter, so FastAPI answers 422.
        """
        response = client.get(
            "/api/v1/auth/google/callback",
            params={"state": "test_state"},
        )

        assert response.status_code == 422

    def test_missing_state_returns_error(self, client):
        """Should reject a callback without the CSRF state."""
        response = client.get(
            "/api/v1/auth/google/callback",
            params={"code": "test_code"},
        )

        assert response.status_code == 422


class TestRefreshEndpoint:
    """Tests for POST /api/v1/auth/refresh"""

    def test_missing_token_returns_error(self, client):
        """Should return error if refresh token cookie is missing."""
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401

    def test_invalid_token_returns_error(self, client):
        """Should return error for invalid refresh token."""
        client.cookies.set("refresh_token", "invalid_token")
        try:
            response = client.post("/api/v1/auth/refresh")
        finally:
            client.cookies.clear()

        assert response.status_code == 401


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me"""

    def test_unauthenticated_returns_error(self, client):
        """Should return error if not authenticated."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers


class TestRateLimiting:
    """Tests for rate limiting on auth endpoints."""

    def test_auth_endpoint_survives_rate_limit_middleware(self, client):
        """The endpoint answers with the rate-limit middleware in the stack.

        The X-RateLimit-* headers are deliberately not asserted: the middleware
        fails open when Redis is unavailable, so their presence depends on the
        environment, not on the endpoint.
        """
        response = client.get("/api/v1/auth/google")

        assert response.status_code == 302
