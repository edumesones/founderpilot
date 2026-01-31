"""Unit tests for BillingService."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.billing_service import BillingService
from src.models.billing import Plan, Subscription


class TestBillingService:
    """Tests for BillingService."""

    def test_get_active_plans(self, db_session, sample_plan):
        """Test retrieving active plans."""
        service = BillingService(db_session)
        plans = service.get_active_plans()

        assert len(plans) == 1
        assert plans[0].id == "price_bundle_test"
        assert plans[0].name == "Bundle"
        assert plans[0].price_cents == 4900

    def test_get_subscription(self, db_session, sample_subscription):
        """Test retrieving a subscription."""
        service = BillingService(db_session)
        sub = service.get_subscription(sample_subscription.tenant_id)

        assert sub is not None
        assert sub.status == "trial"
        assert sub.stripe_customer_id == "cus_test123"

    def test_get_subscription_not_found(self, db_session):
        """Test retrieving non-existent subscription."""
        service = BillingService(db_session)
        sub = service.get_subscription(uuid4())

        assert sub is None

    def test_create_trial_subscription(self, db_session, mock_stripe):
        """Test creating a trial subscription."""
        service = BillingService(db_session)
        tenant_id = uuid4()

        sub = service.create_trial_subscription(
            tenant_id=tenant_id,
            email="test@example.com",
        )

        assert sub.tenant_id == tenant_id
        assert sub.status == "trial"
        assert sub.stripe_customer_id == "cus_test123"
        assert sub.trial_ends_at is not None

        # Verify Stripe Customer was created
        mock_stripe["customer"].assert_called_once()

    def test_create_trial_subscription_already_exists(
        self, db_session, sample_subscription, mock_stripe
    ):
        """Test creating trial when subscription already exists."""
        service = BillingService(db_session)

        # Should return existing subscription
        sub = service.create_trial_subscription(
            tenant_id=sample_subscription.tenant_id,
            email="test@example.com",
        )

        assert sub.id == sample_subscription.id
        # Stripe Customer should NOT be called
        mock_stripe["customer"].assert_not_called()

    def test_subscription_is_active(self, db_session, sample_subscription):
        """Test subscription is_active property."""
        assert sample_subscription.is_active is True

        sample_subscription.status = "canceled"
        assert sample_subscription.is_active is False

    def test_days_remaining_in_trial(self, db_session):
        """Test days_remaining_in_trial property."""
        tenant_id = uuid4()
        sub = Subscription(
            tenant_id=tenant_id,
            stripe_customer_id="cus_test",
            status="trial",
            trial_ends_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(sub)
        db_session.commit()

        # Should be approximately 7 days (might be 6 depending on timing)
        assert sub.days_remaining_in_trial in (6, 7)

    def test_days_remaining_not_in_trial(self, db_session, sample_subscription):
        """Test days_remaining when not in trial."""
        sample_subscription.status = "active"
        db_session.commit()

        assert sample_subscription.days_remaining_in_trial is None

    def test_check_expired_trials(self, db_session):
        """Test checking and expiring old trials."""
        service = BillingService(db_session)

        # Create an expired trial
        tenant_id = uuid4()
        sub = Subscription(
            tenant_id=tenant_id,
            stripe_customer_id="cus_expired",
            status="trial",
            trial_ends_at=datetime.utcnow() - timedelta(days=1),
        )
        db_session.add(sub)
        db_session.commit()

        # Run expiration check
        expired_count = service.check_expired_trials()

        assert expired_count == 1
        db_session.refresh(sub)
        assert sub.status == "expired"


class TestBillingServiceCheckout:
    """Tests for checkout functionality."""

    def test_create_checkout_session(
        self, db_session, sample_subscription, mock_stripe
    ):
        """Test creating a checkout session."""
        service = BillingService(db_session)

        url = service.create_checkout_session(
            tenant_id=sample_subscription.tenant_id,
            price_id="price_bundle_test",
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel",
        )

        assert url == "https://checkout.stripe.com/test"
        mock_stripe["checkout"].assert_called_once()

    def test_create_checkout_already_active(
        self, db_session, sample_subscription, mock_stripe
    ):
        """Test creating checkout when already active."""
        sample_subscription.status = "active"
        db_session.commit()

        service = BillingService(db_session)

        with pytest.raises(ValueError, match="Already have an active subscription"):
            service.create_checkout_session(
                tenant_id=sample_subscription.tenant_id,
                price_id="price_bundle_test",
                success_url="https://app.com/success",
                cancel_url="https://app.com/cancel",
            )


class TestBillingServicePortal:
    """Tests for customer portal functionality."""

    def test_create_portal_session(
        self, db_session, sample_subscription, mock_stripe
    ):
        """Test creating a portal session."""
        service = BillingService(db_session)

        url = service.create_portal_session(
            tenant_id=sample_subscription.tenant_id,
            return_url="https://app.com/billing",
        )

        assert url == "https://billing.stripe.com/test"
        mock_stripe["portal"].assert_called_once()

    def test_create_portal_no_subscription(self, db_session, mock_stripe):
        """Test creating portal without subscription."""
        service = BillingService(db_session)

        with pytest.raises(ValueError, match="No subscription found"):
            service.create_portal_session(
                tenant_id=uuid4(),
                return_url="https://app.com/billing",
            )
