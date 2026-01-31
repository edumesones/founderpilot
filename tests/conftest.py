"""Pytest configuration and fixtures."""
import os
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from src.core.database import Base
from src.models.billing import Plan, Subscription


# =============================================================================
# Environment Setup
# =============================================================================

# Set test environment for Slack
os.environ["DATABASE_URL"] = "postgresql://localhost/founderpilot_test"
os.environ["ENCRYPTION_KEY"] = "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcw=="  # Test key

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


# =============================================================================
# Database Fixtures
# =============================================================================

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
def mock_db():
    """Mock database session (for unit tests without real DB)."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


# =============================================================================
# Billing Fixtures (FEAT-002)
# =============================================================================

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


# =============================================================================
# Slack Fixtures (FEAT-006)
# =============================================================================

@pytest.fixture
def mock_slack_client():
    """Mock Slack WebClient."""
    with patch("slack_sdk.WebClient") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_workflow_id():
    """Sample workflow ID for testing."""
    return UUID("87654321-4321-8765-4321-876543218765")


@pytest.fixture
def sample_email_payload(sample_workflow_id):
    """Sample email notification payload."""
    from src.schemas.slack import EmailNotificationPayload

    return EmailNotificationPayload(
        workflow_id=sample_workflow_id,
        sender="john@client.com",
        subject="Contract renewal question",
        classification="URGENT",
        confidence=75,
        proposed_response="Hi John, Thanks for reaching out about the renewal...",
        email_snippet="I wanted to discuss the terms of our contract renewal...",
    )


@pytest.fixture
def sample_invoice_payload(sample_workflow_id):
    """Sample invoice notification payload (for Slack, not billing)."""
    from src.schemas.slack import InvoiceNotificationPayload

    return InvoiceNotificationPayload(
        workflow_id=sample_workflow_id,
        client_name="Acme Corp",
        invoice_number="INV-2026-001",
        amount="$1,500.00",
        due_date="January 15, 2026",
        days_overdue=5,
        proposed_action="Send a friendly reminder email about the overdue payment.",
    )


@pytest.fixture
def sample_meeting_payload(sample_workflow_id):
    """Sample meeting notification payload."""
    from src.schemas.slack import MeetingNotificationPayload

    return MeetingNotificationPayload(
        workflow_id=sample_workflow_id,
        meeting_title="Q1 Planning Session",
        start_time=datetime(2026, 2, 1, 10, 0),
        attendees=["Alice", "Bob", "Charlie"],
        context_summary="This is a quarterly planning meeting with the leadership team.",
        proposed_prep="Review Q4 metrics, prepare 3 key initiatives for Q1.",
    )
