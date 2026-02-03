"""Unit tests for UsageTracker service."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.billing import Subscription, Plan
from src.models.usage import UsageEvent, UsageCounter
from src.services.usage_tracker import UsageTracker


class TestUsageTracker:
    """Test suite for UsageTracker service."""

    @pytest.fixture
    def tenant_id(self):
        """Generate a tenant ID."""
        return uuid4()

    @pytest.fixture
    def plan(self, db_session):
        """Create a test plan."""
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
    def subscription(self, db_session, tenant_id, plan):
        """Create a test subscription."""
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
    def usage_tracker(self, db_session):
        """Create a UsageTracker instance."""
        return UsageTracker(db_session)

    def test_track_event_creates_event_and_increments_counter(
        self, usage_tracker, db_session, tenant_id, subscription
    ):
        """Test that track_event creates event and increments counter atomically."""
        # Act
        event = usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="inbox",
            action_type="email_processed",
            resource_id=uuid4(),
            quantity=1,
            metadata={"test": "data"},
        )

        db_session.commit()

        # Assert event created
        assert event.id is not None
        assert event.tenant_id == tenant_id
        assert event.agent == "inbox"
        assert event.action_type == "email_processed"
        assert event.quantity == 1
        assert event.metadata == {"test": "data"}
        assert event.idempotency_key is not None

        # Assert counter incremented
        counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "inbox",
            )
            .first()
        )
        assert counter is not None
        assert counter.count == 1
        assert counter.last_event_at is not None

    def test_track_event_increments_existing_counter(
        self, usage_tracker, db_session, tenant_id, subscription
    ):
        """Test that track_event increments existing counter."""
        # Create first event
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="inbox",
            action_type="email_processed",
        )
        db_session.commit()

        # Create second event
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="inbox",
            action_type="email_processed",
        )
        db_session.commit()

        # Assert counter incremented to 2
        counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "inbox",
            )
            .first()
        )
        assert counter.count == 2

    def test_track_event_rejects_duplicate_idempotency_key(
        self, usage_tracker, db_session, tenant_id, subscription, monkeypatch
    ):
        """Test that track_event rejects duplicate events based on idempotency key."""
        # Mock timestamp to generate same idempotency key
        fixed_timestamp = datetime(2026, 1, 1, 12, 0, 0)

        def mock_utcnow():
            return fixed_timestamp

        monkeypatch.setattr("src.services.usage_tracker.datetime", type("datetime", (), {"utcnow": staticmethod(mock_utcnow)}))
        monkeypatch.setattr("src.models.usage.datetime", type("datetime", (), {"utcnow": staticmethod(mock_utcnow)}))

        resource_id = uuid4()

        # Create first event
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="inbox",
            action_type="email_processed",
            resource_id=resource_id,
        )
        db_session.commit()

        # Try to create duplicate event with same parameters
        with pytest.raises(IntegrityError):
            usage_tracker.track_event(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
                resource_id=resource_id,
            )

        # Counter should still be 1 (duplicate rejected)
        counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "inbox",
            )
            .first()
        )
        assert counter.count == 1

    def test_track_event_creates_counter_for_new_period(
        self, usage_tracker, db_session, tenant_id, subscription
    ):
        """Test that track_event creates counter for current billing period."""
        # Act
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="invoice",
            action_type="invoice_detected",
        )
        db_session.commit()

        # Assert counter created with correct period
        counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "invoice",
            )
            .first()
        )
        assert counter is not None
        assert counter.period_start == subscription.current_period_start
        assert counter.period_end == subscription.current_period_end
        assert counter.count == 1

    def test_track_event_raises_error_for_no_subscription(
        self, usage_tracker, db_session
    ):
        """Test that track_event raises ValueError when tenant has no subscription."""
        tenant_without_subscription = uuid4()

        with pytest.raises(ValueError, match="has no subscription"):
            usage_tracker.track_event(
                tenant_id=tenant_without_subscription,
                agent="inbox",
                action_type="email_processed",
            )

    def test_track_event_raises_error_for_invalid_agent(
        self, usage_tracker, tenant_id, subscription
    ):
        """Test that track_event raises ValueError for invalid agent type."""
        with pytest.raises(ValueError, match="Invalid agent type"):
            usage_tracker.track_event(
                tenant_id=tenant_id,
                agent="invalid_agent",
                action_type="some_action",
            )

    def test_track_event_handles_quantity_parameter(
        self, usage_tracker, db_session, tenant_id, subscription
    ):
        """Test that track_event respects quantity parameter."""
        # Create event with quantity=5
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="meeting",
            action_type="meeting_prep",
            quantity=5,
        )
        db_session.commit()

        # Assert counter incremented by 5
        counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "meeting",
            )
            .first()
        )
        assert counter.count == 5

    def test_track_event_transaction_rollback_on_failure(
        self, usage_tracker, db_session, tenant_id, subscription, monkeypatch
    ):
        """Test that transaction rolls back on failure, leaving DB consistent."""
        # Create first successful event
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="inbox",
            action_type="email_processed",
        )
        db_session.commit()

        # Mock flush to raise an error after event creation but before commit
        original_flush = db_session.flush

        def mock_flush():
            if db_session.new:
                raise Exception("Simulated database error")
            original_flush()

        monkeypatch.setattr(db_session, "flush", mock_flush)

        # Try to create second event that will fail
        with pytest.raises(Exception, match="Simulated database error"):
            usage_tracker.track_event(
                tenant_id=tenant_id,
                agent="inbox",
                action_type="email_processed",
            )

        # Verify counter is still 1 (not incremented by failed transaction)
        db_session.rollback()
        counter = (
            db_session.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == "inbox",
            )
            .first()
        )
        assert counter.count == 1

    def test_track_event_separate_counters_per_agent(
        self, usage_tracker, db_session, tenant_id, subscription
    ):
        """Test that each agent type has separate counter."""
        # Create events for different agents
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="inbox",
            action_type="email_processed",
        )
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="invoice",
            action_type="invoice_detected",
        )
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="meeting",
            action_type="meeting_prep",
        )
        db_session.commit()

        # Assert separate counters created
        counters = (
            db_session.query(UsageCounter)
            .filter(UsageCounter.tenant_id == tenant_id)
            .all()
        )
        assert len(counters) == 3

        agent_counts = {c.agent: c.count for c in counters}
        assert agent_counts["inbox"] == 1
        assert agent_counts["invoice"] == 1
        assert agent_counts["meeting"] == 1

    def test_get_current_count(
        self, usage_tracker, db_session, tenant_id, subscription
    ):
        """Test get_current_count returns correct count."""
        # Create some events
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="inbox",
            action_type="email_processed",
        )
        usage_tracker.track_event(
            tenant_id=tenant_id,
            agent="inbox",
            action_type="email_processed",
        )
        db_session.commit()

        # Get count
        count = usage_tracker.get_current_count(tenant_id, "inbox")
        assert count == 2

    def test_get_current_count_returns_zero_for_no_subscription(
        self, usage_tracker
    ):
        """Test get_current_count returns 0 when no subscription exists."""
        tenant_without_subscription = uuid4()
        count = usage_tracker.get_current_count(
            tenant_without_subscription, "inbox"
        )
        assert count == 0

    def test_idempotency_key_format(self, usage_tracker, tenant_id):
        """Test idempotency key generation format."""
        resource_id = uuid4()
        key = usage_tracker._generate_idempotency_key(
            tenant_id, "inbox", "email_processed", resource_id
        )

        # Format: {tenant_id}:{agent}:{resource_id}:{action_type}:{timestamp_ms}
        parts = key.split(":")
        assert len(parts) == 5
        assert parts[0] == str(tenant_id)
        assert parts[1] == "inbox"
        assert parts[2] == str(resource_id)
        assert parts[3] == "email_processed"
        assert parts[4].isdigit()  # timestamp_ms

    def test_idempotency_key_without_resource_id(self, usage_tracker, tenant_id):
        """Test idempotency key generation without resource_id."""
        key = usage_tracker._generate_idempotency_key(
            tenant_id, "inbox", "email_processed", None
        )

        parts = key.split(":")
        assert parts[2] == "none"  # resource_id placeholder
