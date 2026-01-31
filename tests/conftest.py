"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from uuid import uuid4

from src.core.database import Base
from src.models.billing import Plan, Subscription


# Use SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def sample_plan(db_session):
    """Create a sample plan for testing."""
    plan = Plan(
        id="price_bundle_test",
        stripe_product_id="prod_test",
        name="Bundle",
        description="All agents included",
        price_cents=4900,
        interval="month",
        agents_included=["inbox", "invoice", "meeting"],
        limits={
            "emails_per_month": 500,
            "invoices_per_month": 50,
            "meetings_per_month": 30,
        },
        is_active=True,
    )
    db_session.add(plan)
    db_session.commit()
    return plan


@pytest.fixture
def sample_subscription(db_session):
    """Create a sample trial subscription for testing."""
    tenant_id = uuid4()
    subscription = Subscription(
        tenant_id=tenant_id,
        stripe_customer_id="cus_test123",
        status="trial",
        trial_ends_at=datetime.utcnow() + timedelta(days=14),
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=14),
    )
    db_session.add(subscription)
    db_session.commit()
    return subscription


@pytest.fixture
def mock_stripe():
    """Mock Stripe API calls."""
    with patch("stripe.Customer.create") as mock_customer, \
         patch("stripe.checkout.Session.create") as mock_checkout, \
         patch("stripe.billing_portal.Session.create") as mock_portal, \
         patch("stripe.Subscription.retrieve") as mock_sub_retrieve, \
         patch("stripe.Webhook.construct_event") as mock_webhook:

        mock_customer.return_value = MagicMock(id="cus_test123")
        mock_checkout.return_value = MagicMock(url="https://checkout.stripe.com/test")
        mock_portal.return_value = MagicMock(url="https://billing.stripe.com/test")
        mock_sub_retrieve.return_value = MagicMock(
            id="sub_test123",
            items=MagicMock(data=[MagicMock(price=MagicMock(id="price_test"))]),
            current_period_start=datetime.utcnow().timestamp(),
            current_period_end=(datetime.utcnow() + timedelta(days=30)).timestamp(),
        )

        yield {
            "customer": mock_customer,
            "checkout": mock_checkout,
            "portal": mock_portal,
            "subscription": mock_sub_retrieve,
            "webhook": mock_webhook,
        }
