"""Unit tests for UsageService."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.models.billing import Subscription, Plan
from src.models.usage import UsageCounter
from src.schemas.usage import AgentUsage, UsageAlert
from src.services.usage_service import UsageService


class TestUsageService:
    """Test suite for UsageService."""

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
    def usage_service(self, db_session):
        """Create a UsageService instance."""
        return UsageService(db_session)

    def test_get_usage_stats_returns_correct_data(
        self, usage_service, db_session, tenant_id, subscription, plan
    ):
        """Test get_usage_stats returns complete and correct data."""
        # Create counters
        counter_inbox = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=500,
        )
        counter_invoice = UsageCounter(
            tenant_id=tenant_id,
            agent="invoice",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=50,
        )
        db_session.add_all([counter_inbox, counter_invoice])
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert
        assert stats.tenant_id == tenant_id
        assert stats.period_start == subscription.current_period_start
        assert stats.period_end == subscription.current_period_end
        assert stats.plan.name == "Professional"

        # Check inbox usage
        assert stats.usage["inbox"].count == 500
        assert stats.usage["inbox"].limit == 1000
        assert stats.usage["inbox"].percentage == 50
        assert stats.usage["inbox"].overage == 0
        assert stats.usage["inbox"].overage_cost_cents == 0

        # Check invoice usage
        assert stats.usage["invoice"].count == 50
        assert stats.usage["invoice"].limit == 100
        assert stats.usage["invoice"].percentage == 50

        # Check meeting usage (no counter, should be 0)
        assert stats.usage["meeting"].count == 0
        assert stats.usage["meeting"].limit == 50
        assert stats.usage["meeting"].percentage == 0

    def test_overage_calculation_inbox(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test overage calculation for inbox agent ($0.02/email)."""
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

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert
        assert stats.usage["inbox"].count == 1200
        assert stats.usage["inbox"].limit == 1000
        assert stats.usage["inbox"].percentage == 120
        assert stats.usage["inbox"].overage == 200
        assert stats.usage["inbox"].overage_cost_cents == 400  # 200 * $0.02 = $4.00

    def test_overage_calculation_invoice(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test overage calculation for invoice agent ($0.10/invoice)."""
        # Create counter with overage
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="invoice",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=150,  # 50 over limit
        )
        db_session.add(counter)
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert
        assert stats.usage["invoice"].overage == 50
        assert stats.usage["invoice"].overage_cost_cents == 500  # 50 * $0.10 = $5.00

    def test_overage_calculation_meeting(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test overage calculation for meeting agent ($0.15/meeting)."""
        # Create counter with overage
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="meeting",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=60,  # 10 over limit
        )
        db_session.add(counter)
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert
        assert stats.usage["meeting"].overage == 10
        assert stats.usage["meeting"].overage_cost_cents == 150  # 10 * $0.15 = $1.50

    def test_total_overage_cost_calculation(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test total overage cost across all agents."""
        # Create counters with overage for all agents
        counters = [
            UsageCounter(
                tenant_id=tenant_id,
                agent="inbox",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=1100,  # 100 over = $2.00
            ),
            UsageCounter(
                tenant_id=tenant_id,
                agent="invoice",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=110,  # 10 over = $1.00
            ),
            UsageCounter(
                tenant_id=tenant_id,
                agent="meeting",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=60,  # 10 over = $1.50
            ),
        ]
        db_session.add_all(counters)
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert
        expected_total = 200 + 100 + 150  # $4.50 total
        assert stats.total_overage_cost_cents == expected_total

    def test_alert_generation_warning_at_80_percent(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test that warning alert is generated at 80% usage."""
        # Create counter at 80%
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=800,  # 80% of 1000
        )
        db_session.add(counter)
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert
        assert len(stats.alerts) == 1
        alert = stats.alerts[0]
        assert alert.agent == "inbox"
        assert alert.level == "warning"
        assert "80%" in alert.message

    def test_alert_generation_error_at_100_percent(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test that error alert is generated at 100%+ usage."""
        # Create counter at 120%
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=1200,  # 120% of 1000
        )
        db_session.add(counter)
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert
        assert len(stats.alerts) == 1
        alert = stats.alerts[0]
        assert alert.agent == "inbox"
        assert alert.level == "error"
        assert "exceeded" in alert.message.lower()
        assert "$4.00" in alert.message  # Overage cost

    def test_alert_generation_multiple_agents(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test multiple alerts for different agents."""
        # Create counters: inbox at 85%, invoice at 110%
        counters = [
            UsageCounter(
                tenant_id=tenant_id,
                agent="inbox",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=850,  # 85% - warning
            ),
            UsageCounter(
                tenant_id=tenant_id,
                agent="invoice",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=110,  # 110% - error
            ),
        ]
        db_session.add_all(counters)
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert
        assert len(stats.alerts) == 2

        # Check inbox warning
        inbox_alert = next(a for a in stats.alerts if a.agent == "inbox")
        assert inbox_alert.level == "warning"

        # Check invoice error
        invoice_alert = next(a for a in stats.alerts if a.agent == "invoice")
        assert invoice_alert.level == "error"

    def test_no_alerts_below_80_percent(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test that no alerts are generated below 80% usage."""
        # Create counter at 75%
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=750,
        )
        db_session.add(counter)
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert
        assert len(stats.alerts) == 0

    def test_edge_case_no_counters_yet(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test edge case where no counters exist yet (0 usage)."""
        # Act - no counters created
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert - all counts should be 0
        assert stats.usage["inbox"].count == 0
        assert stats.usage["invoice"].count == 0
        assert stats.usage["meeting"].count == 0
        assert stats.total_overage_cost_cents == 0
        assert len(stats.alerts) == 0

    def test_edge_case_trial_user_no_limits(self, usage_service, db_session, tenant_id):
        """Test trial user with no limits (or limits set to 0)."""
        # Create trial plan with no limits
        trial_plan = Plan(
            name="Trial",
            stripe_price_id="price_trial",
            price_cents=0,
            limits={
                "emails_per_month": 0,
                "invoices_per_month": 0,
                "meetings_per_month": 0,
            },
        )
        db_session.add(trial_plan)

        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=trial_plan.id,
            stripe_subscription_id="sub_trial",
            status="trial",
            current_period_start=now,
            current_period_end=now + timedelta(days=14),
        )
        db_session.add(subscription)
        db_session.commit()

        # Create counter with high usage
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=10000,  # High usage
        )
        db_session.add(counter)
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert - should have effectively unlimited limit
        assert stats.usage["inbox"].limit == 999999
        assert stats.usage["inbox"].percentage == 1  # 10000/999999 * 100 ~= 1%
        assert stats.usage["inbox"].overage == 0
        assert len(stats.alerts) == 0  # No alerts for trial

    def test_raises_404_when_no_subscription(self, usage_service):
        """Test that 404 is raised when tenant has no subscription."""
        tenant_without_subscription = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            usage_service.get_usage_stats(tenant_without_subscription)

        assert exc_info.value.status_code == 404
        assert "No subscription found" in exc_info.value.detail

    def test_raises_403_when_subscription_not_active(
        self, usage_service, db_session, tenant_id, plan
    ):
        """Test that 403 is raised when subscription is not active."""
        # Create inactive subscription
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            stripe_subscription_id="sub_inactive",
            status="canceled",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            usage_service.get_usage_stats(tenant_id)

        assert exc_info.value.status_code == 403
        assert "not active" in exc_info.value.detail

    def test_raises_500_when_subscription_has_no_plan(
        self, usage_service, db_session, tenant_id
    ):
        """Test that 500 is raised when subscription has no plan assigned."""
        # Create subscription without plan
        now = datetime.utcnow()
        subscription = Subscription(
            tenant_id=tenant_id,
            plan_id=None,  # No plan
            stripe_subscription_id="sub_no_plan",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db_session.add(subscription)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            usage_service.get_usage_stats(tenant_id)

        assert exc_info.value.status_code == 500
        assert "no plan assigned" in exc_info.value.detail

    def test_get_usage_for_agent(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test get_usage_for_agent helper method."""
        # Create counter
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=500,
        )
        db_session.add(counter)
        db_session.commit()

        # Act
        usage = usage_service.get_usage_for_agent(tenant_id, "inbox")

        # Assert
        assert usage is not None
        assert usage.count == 500
        assert usage.agent == "inbox"

    def test_get_usage_for_agent_returns_none_when_no_subscription(
        self, usage_service
    ):
        """Test get_usage_for_agent returns None when no subscription."""
        tenant_without_subscription = uuid4()

        usage = usage_service.get_usage_for_agent(
            tenant_without_subscription, "inbox"
        )

        assert usage is None

    def test_percentage_calculation_edge_cases(
        self, usage_service, db_session, tenant_id, subscription
    ):
        """Test percentage calculation edge cases."""
        # Create counter exactly at limit
        counter = UsageCounter(
            tenant_id=tenant_id,
            agent="inbox",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            count=1000,  # Exactly at limit
        )
        db_session.add(counter)
        db_session.commit()

        # Act
        stats = usage_service.get_usage_stats(tenant_id)

        # Assert - exactly 100%
        assert stats.usage["inbox"].percentage == 100
        assert stats.usage["inbox"].overage == 0  # No overage at exactly 100%

    def test_overage_pricing_constants(self, usage_service):
        """Test that overage pricing constants are set correctly."""
        assert usage_service.OVERAGE_PRICING["inbox"] == 2  # $0.02
        assert usage_service.OVERAGE_PRICING["invoice"] == 10  # $0.10
        assert usage_service.OVERAGE_PRICING["meeting"] == 15  # $0.15

    def test_limit_key_mapping(self, usage_service):
        """Test that limit key mapping is correct."""
        assert usage_service.LIMIT_KEY_MAP["inbox"] == "emails_per_month"
        assert usage_service.LIMIT_KEY_MAP["invoice"] == "invoices_per_month"
        assert usage_service.LIMIT_KEY_MAP["meeting"] == "meetings_per_month"
