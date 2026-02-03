"""
Integration tests for usage API routes.

Tests the full request/response cycle for usage tracking endpoints including:
- Authentication and authorization
- Tenant isolation
- Usage statistics retrieval
- Error handling (no subscription, inactive subscription)
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.billing import Plan, Subscription
from src.models.usage import UsageCounter


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_current_user():
    """Mock current user for authentication."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    return user


@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {"Authorization": "Bearer mock_token"}


@pytest.fixture
def plan(db_session):
    """Create test plan."""
    plan = Plan(
        name="Professional",
        stripe_price_id="price_test_123",
        price_cents=4900,
        limits={
            "emails_per_month": 1000,
            "invoices_per_month": 100,
            "meetings_per_month": 50,
        },
    )
    db_session.add(plan)
    db_session.commit()
    return plan


@pytest.fixture
def subscription(db_session, mock_current_user, plan):
    """Create test subscription."""
    now = datetime.utcnow()
    subscription = Subscription(
        tenant_id=mock_current_user.id,
        plan_id=plan.id,
        stripe_subscription_id="sub_test_123",
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db_session.add(subscription)
    db_session.commit()
    return subscription


class TestGetUsageStatsEndpoint:
    """Tests for GET /api/v1/usage"""

    def test_requires_authentication(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/v1/usage")
        assert response.status_code == 401

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_get_usage_stats_success(
        self, mock_db, mock_auth, client, mock_current_user, db_session, subscription
    ):
        """Test successfully retrieving usage stats."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create counters
        counters = [
            UsageCounter(
                tenant_id=mock_current_user.id,
                agent="inbox",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=500,
            ),
            UsageCounter(
                tenant_id=mock_current_user.id,
                agent="invoice",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=50,
            ),
        ]
        db_session.add_all(counters)
        db_session.commit()

        response = client.get("/api/v1/usage")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "tenant_id" in data
        assert "period_start" in data
        assert "period_end" in data
        assert "plan" in data
        assert "usage" in data
        assert "total_overage_cost_cents" in data
        assert "alerts" in data

        # Check plan info
        assert data["plan"]["name"] == "Professional"

        # Check usage data
        assert data["usage"]["inbox"]["count"] == 500
        assert data["usage"]["inbox"]["limit"] == 1000
        assert data["usage"]["inbox"]["percentage"] == 50
        assert data["usage"]["inbox"]["overage"] == 0

        assert data["usage"]["invoice"]["count"] == 50
        assert data["usage"]["invoice"]["limit"] == 100
        assert data["usage"]["invoice"]["percentage"] == 50

        assert data["usage"]["meeting"]["count"] == 0
        assert data["usage"]["meeting"]["limit"] == 50

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_get_usage_stats_with_overage(
        self, mock_db, mock_auth, client, mock_current_user, db_session, subscription
    ):
        """Test usage stats with overage charges."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create counter with overage
        counter = UsageCounter(
            tenant_id=mock_current_user.id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=1200,  # 200 over limit
        )
        db_session.add(counter)
        db_session.commit()

        response = client.get("/api/v1/usage")

        assert response.status_code == 200
        data = response.json()

        # Check overage calculation
        assert data["usage"]["inbox"]["count"] == 1200
        assert data["usage"]["inbox"]["overage"] == 200
        assert data["usage"]["inbox"]["overage_cost_cents"] == 400  # 200 * $0.02
        assert data["total_overage_cost_cents"] == 400

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_get_usage_stats_with_alerts(
        self, mock_db, mock_auth, client, mock_current_user, db_session, subscription
    ):
        """Test usage stats includes alerts for high usage."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create counters: inbox at 85%, invoice at 110%
        counters = [
            UsageCounter(
                tenant_id=mock_current_user.id,
                agent="inbox",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=850,  # 85% - warning
            ),
            UsageCounter(
                tenant_id=mock_current_user.id,
                agent="invoice",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=110,  # 110% - error
            ),
        ]
        db_session.add_all(counters)
        db_session.commit()

        response = client.get("/api/v1/usage")

        assert response.status_code == 200
        data = response.json()

        # Check alerts
        assert len(data["alerts"]) == 2

        # Find inbox warning
        inbox_alert = next(a for a in data["alerts"] if a["agent"] == "inbox")
        assert inbox_alert["level"] == "warning"
        assert "85%" in inbox_alert["message"]

        # Find invoice error
        invoice_alert = next(a for a in data["alerts"] if a["agent"] == "invoice")
        assert invoice_alert["level"] == "error"
        assert "exceeded" in invoice_alert["message"].lower()

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_get_usage_stats_no_counters_yet(
        self, mock_db, mock_auth, client, mock_current_user, db_session, subscription
    ):
        """Test usage stats when no counters exist yet (new billing period)."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        response = client.get("/api/v1/usage")

        assert response.status_code == 200
        data = response.json()

        # All counts should be 0
        assert data["usage"]["inbox"]["count"] == 0
        assert data["usage"]["invoice"]["count"] == 0
        assert data["usage"]["meeting"]["count"] == 0
        assert data["total_overage_cost_cents"] == 0
        assert len(data["alerts"]) == 0

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_returns_404_when_no_subscription(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test that 404 is returned when user has no subscription."""
        # User exists but no subscription created
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        response = client.get("/api/v1/usage")

        assert response.status_code == 404
        assert "No subscription found" in response.json()["detail"]

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_returns_403_when_subscription_inactive(
        self, mock_db, mock_auth, client, mock_current_user, db_session, plan
    ):
        """Test that 403 is returned when subscription is not active."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create inactive subscription
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=mock_current_user.id,
            plan_id=plan.id,
            stripe_subscription_id="sub_inactive",
            status="canceled",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)
        db_session.commit()

        response = client.get("/api/v1/usage")

        assert response.status_code == 403
        assert "not active" in response.json()["detail"]

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_tenant_isolation(
        self, mock_db, mock_auth, client, mock_current_user, db_session, plan
    ):
        """Test that users can only see their own usage data."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create subscription for current user
        now = datetime.utcnow()
        subscription1 = Subscription(
            tenant_id=mock_current_user.id,
            plan_id=plan.id,
            stripe_subscription_id="sub_user1",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription1)

        # Create subscription for another user
        other_user_id = uuid4()
        subscription2 = Subscription(
            tenant_id=other_user_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_user2",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription2)

        # Create counters for both users
        counter1 = UsageCounter(
            tenant_id=mock_current_user.id,
            agent="inbox",
            period_start=now,
            period_end=now + timedelta(days=30),
            count=500,
        )
        counter2 = UsageCounter(
            tenant_id=other_user_id,
            agent="inbox",
            period_start=now,
            period_end=now + timedelta(days=30),
            count=999,
        )
        db_session.add_all([counter1, counter2])
        db_session.commit()

        response = client.get("/api/v1/usage")

        assert response.status_code == 200
        data = response.json()

        # Should only see current user's data
        assert str(data["tenant_id"]) == str(mock_current_user.id)
        assert data["usage"]["inbox"]["count"] == 500
        # Should NOT see other user's count (999)

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_response_includes_billing_period_dates(
        self, mock_db, mock_auth, client, mock_current_user, db_session, subscription
    ):
        """Test that response includes current billing period dates."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        response = client.get("/api/v1/usage")

        assert response.status_code == 200
        data = response.json()

        # Check period dates are present and valid
        assert "period_start" in data
        assert "period_end" in data
        assert data["period_start"] is not None
        assert data["period_end"] is not None

        # Parse dates to verify format
        period_start = datetime.fromisoformat(
            data["period_start"].replace("Z", "+00:00")
        )
        period_end = datetime.fromisoformat(data["period_end"].replace("Z", "+00:00"))
        assert period_end > period_start

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_response_includes_plan_info(
        self, mock_db, mock_auth, client, mock_current_user, db_session, subscription
    ):
        """Test that response includes plan information."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        response = client.get("/api/v1/usage")

        assert response.status_code == 200
        data = response.json()

        # Check plan info
        assert "plan" in data
        assert data["plan"]["name"] == "Professional"
        assert "limits" in data["plan"]
        assert data["plan"]["limits"]["emails_per_month"] == 1000
        assert data["plan"]["limits"]["invoices_per_month"] == 100
        assert data["plan"]["limits"]["meetings_per_month"] == 50

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_multiple_overage_agents_sum_correctly(
        self, mock_db, mock_auth, client, mock_current_user, db_session, subscription
    ):
        """Test that overage costs from multiple agents sum correctly."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create counters with overage for all agents
        counters = [
            UsageCounter(
                tenant_id=mock_current_user.id,
                agent="inbox",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=1100,  # 100 over = $2.00 (100 * $0.02)
            ),
            UsageCounter(
                tenant_id=mock_current_user.id,
                agent="invoice",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=110,  # 10 over = $1.00 (10 * $0.10)
            ),
            UsageCounter(
                tenant_id=mock_current_user.id,
                agent="meeting",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=60,  # 10 over = $1.50 (10 * $0.15)
            ),
        ]
        db_session.add_all(counters)
        db_session.commit()

        response = client.get("/api/v1/usage")

        assert response.status_code == 200
        data = response.json()

        # Check individual overage costs
        assert data["usage"]["inbox"]["overage_cost_cents"] == 200  # $2.00
        assert data["usage"]["invoice"]["overage_cost_cents"] == 100  # $1.00
        assert data["usage"]["meeting"]["overage_cost_cents"] == 150  # $1.50

        # Check total overage cost
        assert data["total_overage_cost_cents"] == 450  # $4.50 total
