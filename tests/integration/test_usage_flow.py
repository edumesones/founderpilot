"""
End-to-end integration tests for usage tracking flow.

Tests the complete flow from event tracking through counter updates to API retrieval.
"""

from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.billing import Plan, Subscription
from src.models.usage import UsageCounter, UsageEvent
from src.services.usage_tracker import UsageTracker
from src.workers.tasks.usage_tasks import (
    reset_usage_counters,
    report_overage_to_stripe,
    reconcile_usage_counters,
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def tenant_id():
    """Generate tenant ID."""
    return uuid4()


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
def subscription(db_session, tenant_id, plan):
    """Create test subscription."""
    now = datetime.utcnow()
    subscription = Subscription(
        tenant_id=tenant_id,
        plan_id=plan.id,
        stripe_subscription_id="sub_test_123",
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db_session.add(subscription)
    db_session.commit()
    return subscription


@pytest.fixture
def mock_current_user(tenant_id):
    """Mock current user."""
    from unittest.mock import MagicMock

    user = MagicMock()
    user.id = tenant_id
    user.email = "test@example.com"
    return user


class TestUsageTrackingE2E:
    """End-to-end tests for complete usage tracking flow."""

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_track_event_to_api_retrieval(
        self, mock_db, mock_auth, client, db_session, tenant_id, mock_current_user, subscription
    ):
        """
        Test complete flow: track event → counter incremented → API returns updated stats.
        """
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Step 1: Track usage events
        tracker = UsageTracker(db_session)

        # Track 5 emails
        for i in range(5):
            tracker.track_event(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
                resource_id=uuid4(),
            )
        db_session.commit()

        # Step 2: Verify counter incremented
        counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "inbox",
            )
            .first()
        )
        assert counter is not None
        assert counter.count == 5

        # Step 3: Retrieve via API
        response = client.get("/api/v1/usage")
        assert response.status_code == 200
        data = response.json()

        # Step 4: Verify API response
        assert data["usage"]["inbox"]["count"] == 5
        assert data["usage"]["inbox"]["limit"] == 1000
        assert data["usage"]["inbox"]["percentage"] == 0  # 5/1000 rounds to 0%
        assert data["usage"]["inbox"]["overage"] == 0

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    @patch("src.workers.tasks.usage_tasks.stripe_usage_reporter")
    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_overage_scenario_with_stripe_reporting(
        self,
        mock_session_local,
        mock_stripe_reporter,
        mock_db,
        mock_auth,
        client,
        db_session,
        tenant_id,
        mock_current_user,
        subscription,
    ):
        """
        Test overage scenario: usage exceeds limit → Stripe report triggered → API shows overage cost.
        """
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session
        mock_session_local.return_value = db_session
        mock_stripe_reporter.report_usage.return_value = True

        # Step 1: Track usage that exceeds limit (1200 emails, limit is 1000)
        tracker = UsageTracker(db_session)
        for i in range(1200):
            tracker.track_event(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
                resource_id=uuid4() if i % 100 == 0 else None,  # Vary resource_id for uniqueness
                quantity=1,
            )
        db_session.commit()

        # Step 2: Verify counter shows overage
        counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "inbox",
            )
            .first()
        )
        assert counter.count == 1200

        # Step 3: Run overage reporting task
        result = report_overage_to_stripe()
        assert result["success_count"] == 1

        # Verify Stripe was called with correct overage
        mock_stripe_reporter.report_usage.assert_called_once()
        call_kwargs = mock_stripe_reporter.report_usage.call_args[1]
        assert call_kwargs["quantity"] == 200  # 1200 - 1000 = 200 overage

        # Step 4: Retrieve via API
        response = client.get("/api/v1/usage")
        assert response.status_code == 200
        data = response.json()

        # Step 5: Verify API shows overage and cost
        assert data["usage"]["inbox"]["count"] == 1200
        assert data["usage"]["inbox"]["overage"] == 200
        assert data["usage"]["inbox"]["overage_cost_cents"] == 400  # 200 * $0.02
        assert data["total_overage_cost_cents"] == 400

        # Step 6: Verify error alert generated
        assert len(data["alerts"]) >= 1
        error_alert = next(
            (a for a in data["alerts"] if a["agent"] == "inbox" and a["level"] == "error"),
            None,
        )
        assert error_alert is not None
        assert "exceeded" in error_alert["message"].lower()

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_period_rollover_creates_new_counters(
        self, mock_session_local, db_session, tenant_id, subscription
    ):
        """
        Test period rollover: new billing period → new counters created.
        """
        mock_session_local.return_value = db_session

        # Step 1: Create counter for current period
        now = datetime.utcnow()
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=500,
        )
        db_session.add(counter)
        db_session.commit()

        # Step 2: Simulate period rollover by updating subscription dates
        new_period_start = now + timedelta(days=30)
        new_period_end = now + timedelta(days=60)
        subscription.current_period_start = new_period_start
        subscription.current_period_end = new_period_end
        db_session.commit()

        # Step 3: Run reset task
        result = reset_usage_counters()

        # Step 4: Verify new counters created for new period
        assert result["counters_created"] == 3  # inbox, invoice, meeting

        # Step 5: Verify new counter exists with count=0
        new_counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "inbox",
                UsageCounter.period_start == new_period_start,
            )
            .first()
        )
        assert new_counter is not None
        assert new_counter.count == 0

        # Step 6: Verify old counter still exists with old count
        old_counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "inbox",
                UsageCounter.period_start == now,
            )
            .first()
        )
        assert old_counter is not None
        assert old_counter.count == 500

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_reconciliation_corrects_counter_drift(
        self, mock_session_local, db_session, tenant_id, subscription
    ):
        """
        Test reconciliation: counter drifts from events → auto-corrected.
        """
        mock_session_local.return_value = db_session

        # Step 1: Create counter with incorrect count
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=100,  # Incorrect count
        )
        db_session.add(counter)

        # Step 2: Create events that sum to 103 (3% drift)
        now = datetime.utcnow()
        for i in range(103):
            event = UsageEvent(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
                quantity=1,
                idempotency_key=f"reconcile_key_{i}",
                created_at=subscription.current_period_start + timedelta(minutes=i),
            )
            db_session.add(event)
        db_session.commit()

        # Step 3: Run reconciliation task
        result = reconcile_usage_counters()

        # Step 4: Verify drift detected and corrected
        assert result["drift_detected"] == 1
        assert result["auto_corrected"] == 1

        # Step 5: Verify counter was corrected
        db_session.refresh(counter)
        assert counter.count == 103

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_multiple_agents_tracking_independently(
        self, mock_db, mock_auth, client, db_session, tenant_id, mock_current_user, subscription
    ):
        """
        Test that multiple agents track usage independently.
        """
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Step 1: Track events for all 3 agents
        tracker = UsageTracker(db_session)

        # Track 10 emails
        for i in range(10):
            tracker.track_event(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
            )

        # Track 5 invoices
        for i in range(5):
            tracker.track_event(
                tenant_id=tenant_id,
                agent="invoice",
                action_type="invoice_detected",
            )

        # Track 3 meetings
        for i in range(3):
            tracker.track_event(
                tenant_id=tenant_id,
                agent="meeting",
                action_type="meeting_prep",
            )

        db_session.commit()

        # Step 2: Verify separate counters exist
        counters = (
            db_session.query(UsageCounter)
            .filter(UsageCounter.tenant_id == tenant_id)
            .all()
        )
        assert len(counters) == 3

        agent_counts = {c.agent: c.count for c in counters}
        assert agent_counts["inbox"] == 10
        assert agent_counts["invoice"] == 5
        assert agent_counts["meeting"] == 3

        # Step 3: Retrieve via API
        response = client.get("/api/v1/usage")
        assert response.status_code == 200
        data = response.json()

        # Step 4: Verify API shows all agents
        assert data["usage"]["inbox"]["count"] == 10
        assert data["usage"]["invoice"]["count"] == 5
        assert data["usage"]["meeting"]["count"] == 3

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_idempotency_prevents_duplicate_tracking(
        self, mock_db, mock_auth, client, db_session, tenant_id, mock_current_user, subscription, monkeypatch
    ):
        """
        Test that idempotency prevents duplicate event tracking.
        """
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Mock timestamp to generate same idempotency key
        fixed_timestamp = datetime(2026, 1, 1, 12, 0, 0)

        def mock_utcnow():
            return fixed_timestamp

        monkeypatch.setattr(
            "src.services.usage_tracker.datetime",
            type("datetime", (), {"utcnow": staticmethod(mock_utcnow)}),
        )
        monkeypatch.setattr(
            "src.models.usage.datetime",
            type("datetime", (), {"utcnow": staticmethod(mock_utcnow)}),
        )

        # Step 1: Track event
        tracker = UsageTracker(db_session)
        resource_id = uuid4()

        event1 = tracker.track_event(
            tenant_id=tenant_id,
            agent="inbox",
            action_type="email_processed",
            resource_id=resource_id,
        )
        db_session.commit()

        # Step 2: Try to track duplicate event (same params, same timestamp)
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            tracker.track_event(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
                resource_id=resource_id,
            )

        # Step 3: Verify counter only incremented once
        counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "inbox",
            )
            .first()
        )
        assert counter.count == 1  # Not 2

        # Step 4: Verify only 1 event in database
        event_count = (
            db_session.query(UsageEvent)
            .filter(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.agent == "inbox",
            )
            .count()
        )
        assert event_count == 1

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_alert_threshold_progression(
        self, mock_db, mock_auth, client, db_session, tenant_id, mock_current_user, subscription
    ):
        """
        Test alert progression: no alert → warning at 80% → error at 100%.
        """
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        tracker = UsageTracker(db_session)

        # Step 1: Track to 70% (700 emails, limit 1000) - no alert
        for i in range(700):
            tracker.track_event(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
            )
        db_session.commit()

        response = client.get("/api/v1/usage")
        data = response.json()
        assert len([a for a in data["alerts"] if a["agent"] == "inbox"]) == 0

        # Step 2: Track to 85% (850 total) - warning alert
        for i in range(150):
            tracker.track_event(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
            )
        db_session.commit()

        response = client.get("/api/v1/usage")
        data = response.json()
        inbox_alerts = [a for a in data["alerts"] if a["agent"] == "inbox"]
        assert len(inbox_alerts) == 1
        assert inbox_alerts[0]["level"] == "warning"

        # Step 3: Track to 120% (1200 total) - error alert
        for i in range(350):
            tracker.track_event(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
            )
        db_session.commit()

        response = client.get("/api/v1/usage")
        data = response.json()
        inbox_alerts = [a for a in data["alerts"] if a["agent"] == "inbox"]
        assert len(inbox_alerts) == 1
        assert inbox_alerts[0]["level"] == "error"
        assert "exceeded" in inbox_alerts[0]["message"].lower()


class TestMultiTenantIsolation:
    """E2E tests for tenant isolation."""

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_tenants_cannot_see_each_others_usage(
        self, mock_db, mock_auth, client, db_session, plan
    ):
        """
        Test that tenant isolation is enforced end-to-end.
        """
        # Create 2 tenants
        tenant1_id = uuid4()
        tenant2_id = uuid4()

        now = datetime.utcnow()
        for tenant_id in [tenant1_id, tenant2_id]:
            subscription = Subscription(
                tenant_id=tenant_id,
                plan_id=plan.id,
                stripe_subscription_id=f"sub_{tenant_id}",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
            db_session.add(subscription)
        db_session.commit()

        # Track usage for both tenants
        tracker = UsageTracker(db_session)

        # Tenant 1: 100 emails
        for i in range(100):
            tracker.track_event(
                tenant_id=tenant1_id,
                agent="inbox",
                action_type="email_processed",
            )

        # Tenant 2: 200 emails
        for i in range(200):
            tracker.track_event(
                tenant_id=tenant2_id,
                agent="inbox",
                action_type="email_processed",
            )
        db_session.commit()

        # Mock auth as tenant1
        from unittest.mock import MagicMock

        tenant1_user = MagicMock()
        tenant1_user.id = tenant1_id
        tenant1_user.email = "tenant1@example.com"

        mock_auth.return_value = tenant1_user
        mock_db.return_value = db_session

        # Tenant 1 retrieves usage - should only see their own
        response = client.get("/api/v1/usage")
        assert response.status_code == 200
        data = response.json()
        assert str(data["tenant_id"]) == str(tenant1_id)
        assert data["usage"]["inbox"]["count"] == 100  # Not 200

        # Mock auth as tenant2
        tenant2_user = MagicMock()
        tenant2_user.id = tenant2_id
        tenant2_user.email = "tenant2@example.com"

        mock_auth.return_value = tenant2_user

        # Tenant 2 retrieves usage - should only see their own
        response = client.get("/api/v1/usage")
        assert response.status_code == 200
        data = response.json()
        assert str(data["tenant_id"]) == str(tenant2_id)
        assert data["usage"]["inbox"]["count"] == 200  # Not 100
