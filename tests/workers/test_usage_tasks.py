"""Unit tests for usage tracking Celery tasks."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from stripe.error import StripeError

from src.models.billing import Plan, Subscription
from src.models.usage import UsageCounter, UsageEvent
from src.services.stripe_usage_reporter import CircuitBreakerError
from src.workers.tasks.usage_tasks import (
    reset_usage_counters,
    report_overage_to_stripe,
    reconcile_usage_counters,
    _get_limit_for_agent,
)


class TestResetUsageCountersTask:
    """Tests for reset_usage_counters Celery task."""

    @pytest.fixture
    def plan(self, db_session):
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

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_creates_new_counters_for_new_period(self, mock_session_local, db_session, plan):
        """Test that new counters are created when billing period rolls over."""
        mock_session_local.return_value = db_session

        # Create subscription with new billing period
        tenant_id = uuid4()
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)
        db_session.commit()

        # Run task
        result = reset_usage_counters()

        # Assert counters created
        assert result["counters_created"] == 3  # inbox, invoice, meeting
        assert result["subscriptions_checked"] == 1

        # Verify counters exist
        counters = db_session.query(UsageCounter).filter(
            UsageCounter.tenant_id == tenant_id
        ).all()
        assert len(counters) == 3
        assert {c.agent for c in counters} == {"inbox", "invoice", "meeting"}
        for counter in counters:
            assert counter.count == 0
            assert counter.period_start == subscription.current_period_start

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_skips_existing_counters(self, mock_session_local, db_session, plan):
        """Test that existing counters are not recreated."""
        mock_session_local.return_value = db_session

        # Create subscription
        tenant_id = uuid4()
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)

        # Create existing counter
        existing_counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=100,
        )
        db_session.add(existing_counter)
        db_session.commit()

        # Run task
        result = reset_usage_counters()

        # Assert only 2 new counters created (invoice, meeting)
        assert result["counters_created"] == 2

        # Verify existing counter was not modified
        counter = db_session.query(UsageCounter).filter(
            UsageCounter.tenant_id == tenant_id,
            UsageCounter.agent == "inbox",
        ).first()
        assert counter.count == 100  # Not reset

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_processes_multiple_subscriptions(self, mock_session_local, db_session, plan):
        """Test that task processes all active subscriptions."""
        mock_session_local.return_value = db_session

        # Create 3 subscriptions
        now = datetime.utcnow()
        for i in range(3):
            subscription = Subscription(
                tenant_id=uuid4(),
                plan_id=plan.id,
                stripe_subscription_id=f"sub_{i}",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
            db_session.add(subscription)
        db_session.commit()

        # Run task
        result = reset_usage_counters()

        # Assert
        assert result["subscriptions_checked"] == 3
        assert result["counters_created"] == 9  # 3 subscriptions * 3 agents

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_only_processes_active_subscriptions(self, mock_session_local, db_session, plan):
        """Test that only active/trial subscriptions are processed."""
        mock_session_local.return_value = db_session

        # Create subscriptions with different statuses
        now = datetime.utcnow()
        for status in ["active", "trial", "canceled", "expired"]:
            subscription = Subscription(
                tenant_id=uuid4(),
                plan_id=plan.id,
                stripe_subscription_id=f"sub_{status}",
                status=status,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
            db_session.add(subscription)
        db_session.commit()

        # Run task
        result = reset_usage_counters()

        # Assert only active and trial processed
        assert result["subscriptions_checked"] == 2  # active + trial


class TestReportOverageToStripeTask:
    """Tests for report_overage_to_stripe Celery task."""

    @pytest.fixture
    def plan(self, db_session):
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

    @patch("src.workers.tasks.usage_tasks.stripe_usage_reporter")
    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_reports_overage_to_stripe(self, mock_session_local, mock_reporter, db_session, plan):
        """Test that overage is reported to Stripe."""
        mock_session_local.return_value = db_session
        mock_reporter.report_usage.return_value = True

        # Create subscription
        tenant_id = uuid4()
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)

        # Create counter with overage
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=1200,  # 200 over limit
        )
        db_session.add(counter)
        db_session.commit()

        # Run task
        result = report_overage_to_stripe()

        # Assert
        assert result["success_count"] == 1
        assert result["failure_count"] == 0
        assert result["skipped_count"] == 0

        # Verify Stripe API called
        mock_reporter.report_usage.assert_called_once()
        call_args = mock_reporter.report_usage.call_args
        assert call_args[1]["quantity"] == 200  # Overage amount
        assert "idempotency_key" in call_args[1]

    @patch("src.workers.tasks.usage_tasks.stripe_usage_reporter")
    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_skips_counters_without_overage(self, mock_session_local, mock_reporter, db_session, plan):
        """Test that counters without overage are skipped."""
        mock_session_local.return_value = db_session

        # Create subscription
        tenant_id = uuid4()
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)

        # Create counter without overage
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=500,  # Under limit
        )
        db_session.add(counter)
        db_session.commit()

        # Run task
        result = report_overage_to_stripe()

        # Assert
        assert result["skipped_count"] == 1
        mock_reporter.report_usage.assert_not_called()

    @patch("src.workers.tasks.usage_tasks.stripe_usage_reporter")
    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_continues_after_individual_failure(self, mock_session_local, mock_reporter, db_session, plan):
        """Test that task continues processing after individual Stripe failure."""
        mock_session_local.return_value = db_session

        # Mock Stripe to fail once then succeed
        mock_reporter.report_usage.side_effect = [
            StripeError("API Error"),
            True,
        ]

        # Create 2 subscriptions with overage
        now = datetime.utcnow()
        for i in range(2):
            tenant_id = uuid4()
            subscription = Subscription(
                tenant_id=tenant_id,
                plan_id=plan.id,
                stripe_subscription_id=f"sub_{i}",
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
            db_session.add(subscription)

            counter = UsageCounter(
                tenant_id=tenant_id,
                agent="inbox",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=1200,  # Overage
            )
            db_session.add(counter)
        db_session.commit()

        # Run task
        result = report_overage_to_stripe()

        # Assert - should continue after first failure
        assert result["success_count"] == 1
        assert result["failure_count"] == 1
        assert mock_reporter.report_usage.call_count == 2

    @patch("src.workers.tasks.usage_tasks.stripe_usage_reporter")
    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_aborts_when_circuit_breaker_opens(self, mock_session_local, mock_reporter, db_session, plan):
        """Test that task aborts when circuit breaker opens."""
        mock_session_local.return_value = db_session

        # Mock circuit breaker to open
        mock_reporter.report_usage.side_effect = CircuitBreakerError("Circuit open")

        # Create subscription with overage
        tenant_id = uuid4()
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)

        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=1200,
        )
        db_session.add(counter)
        db_session.commit()

        # Run task
        result = report_overage_to_stripe()

        # Assert - should abort on circuit breaker
        assert result["success_count"] == 0
        assert mock_reporter.report_usage.call_count == 1


class TestReconcileUsageCountersTask:
    """Tests for reconcile_usage_counters Celery task."""

    @pytest.fixture
    def plan(self, db_session):
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

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_auto_corrects_drift_below_5_percent(self, mock_session_local, db_session, plan):
        """Test that drift < 5% is auto-corrected."""
        mock_session_local.return_value = db_session

        # Create subscription
        tenant_id = uuid4()
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)

        # Create counter with incorrect count
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=100,  # Incorrect count
        )
        db_session.add(counter)

        # Create events that sum to 103 (3% drift)
        for i in range(103):
            event = UsageEvent(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
                quantity=1,
                idempotency_key=f"key_{i}",
                created_at=now + timedelta(minutes=i),
            )
            db_session.add(event)
        db_session.commit()

        # Run task
        result = reconcile_usage_counters()

        # Assert
        assert result["drift_detected"] == 1
        assert result["auto_corrected"] == 1
        assert result["high_drift_alerts"] == 0

        # Verify counter was corrected
        db_session.refresh(counter)
        assert counter.count == 103

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_alerts_on_drift_above_5_percent(self, mock_session_local, db_session, plan):
        """Test that drift >= 5% triggers alert without auto-correction."""
        mock_session_local.return_value = db_session

        # Create subscription
        tenant_id = uuid4()
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)

        # Create counter with incorrect count
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=100,  # Incorrect count
        )
        db_session.add(counter)

        # Create events that sum to 110 (10% drift)
        for i in range(110):
            event = UsageEvent(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
                quantity=1,
                idempotency_key=f"key_{i}",
                created_at=now + timedelta(minutes=i),
            )
            db_session.add(event)
        db_session.commit()

        # Run task
        result = reconcile_usage_counters()

        # Assert
        assert result["drift_detected"] == 1
        assert result["auto_corrected"] == 0  # Not auto-corrected
        assert result["high_drift_alerts"] == 1  # Alert generated

        # Verify counter was NOT modified
        db_session.refresh(counter)
        assert counter.count == 100  # Still incorrect

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_handles_no_drift(self, mock_session_local, db_session, plan):
        """Test that correct counters are left unchanged."""
        mock_session_local.return_value = db_session

        # Create subscription
        tenant_id = uuid4()
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)

        # Create counter with correct count
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=100,
        )
        db_session.add(counter)

        # Create exactly 100 events
        for i in range(100):
            event = UsageEvent(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
                quantity=1,
                idempotency_key=f"key_{i}",
                created_at=now + timedelta(minutes=i),
            )
            db_session.add(event)
        db_session.commit()

        # Run task
        result = reconcile_usage_counters()

        # Assert - no drift detected
        assert result["drift_detected"] == 0
        assert result["auto_corrected"] == 0
        assert result["high_drift_alerts"] == 0

    @patch("src.workers.tasks.usage_tasks.SessionLocal")
    def test_handles_zero_events(self, mock_session_local, db_session, plan):
        """Test reconciliation when counter has count but no events."""
        mock_session_local.return_value = db_session

        # Create subscription
        tenant_id = uuid4()
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)

        # Create counter with count but no events
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=50,  # Has count
        )
        db_session.add(counter)
        # No events created
        db_session.commit()

        # Run task
        result = reconcile_usage_counters()

        # Assert - should detect 100% drift and alert
        assert result["drift_detected"] == 1
        assert result["high_drift_alerts"] == 1


class TestGetLimitForAgentHelper:
    """Tests for _get_limit_for_agent helper function."""

    def test_returns_correct_limit_for_inbox(self, db_session):
        """Test that correct limit is returned for inbox agent."""
        plan = Plan(
            name="Test",
            stripe_price_id="price_test",
            price_cents=1000,
            limits={"emails_per_month": 500},
        )
        db_session.add(plan)
        db_session.commit()

        limit = _get_limit_for_agent(plan, "inbox")
        assert limit == 500

    def test_returns_correct_limit_for_invoice(self, db_session):
        """Test that correct limit is returned for invoice agent."""
        plan = Plan(
            name="Test",
            stripe_price_id="price_test",
            price_cents=1000,
            limits={"invoices_per_month": 50},
        )
        db_session.add(plan)
        db_session.commit()

        limit = _get_limit_for_agent(plan, "invoice")
        assert limit == 50

    def test_returns_correct_limit_for_meeting(self, db_session):
        """Test that correct limit is returned for meeting agent."""
        plan = Plan(
            name="Test",
            stripe_price_id="price_test",
            price_cents=1000,
            limits={"meetings_per_month": 25},
        )
        db_session.add(plan)
        db_session.commit()

        limit = _get_limit_for_agent(plan, "meeting")
        assert limit == 25

    def test_returns_zero_for_unknown_agent(self, db_session):
        """Test that 0 is returned for unknown agent type."""
        plan = Plan(
            name="Test",
            stripe_price_id="price_test",
            price_cents=1000,
            limits={},
        )
        db_session.add(plan)
        db_session.commit()

        limit = _get_limit_for_agent(plan, "unknown_agent")
        assert limit == 0

    def test_returns_zero_when_limit_missing(self, db_session):
        """Test that 0 is returned when limit key is missing."""
        plan = Plan(
            name="Test",
            stripe_price_id="price_test",
            price_cents=1000,
            limits={},  # No limits defined
        )
        db_session.add(plan)
        db_session.commit()

        limit = _get_limit_for_agent(plan, "inbox")
        assert limit == 0
