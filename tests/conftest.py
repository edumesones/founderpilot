"""Pytest configuration and fixtures."""

import os
from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker


# =============================================================================
# RSA Key Generation (FEAT-001)
# =============================================================================

def generate_rsa_keys() -> tuple[str, str]:
    """Generate RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


# Generate test RSA keys
TEST_PRIVATE_KEY, TEST_PUBLIC_KEY = generate_rsa_keys()


# =============================================================================
# Environment Setup
# =============================================================================

os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"
os.environ["SLACK_CLIENT_ID"] = "test-slack-client-id"
os.environ["SLACK_CLIENT_SECRET"] = "test-slack-client-secret"
os.environ["SLACK_SIGNING_SECRET"] = "test-slack-signing-secret"
os.environ["JWT_PRIVATE_KEY"] = TEST_PRIVATE_KEY
os.environ["JWT_PUBLIC_KEY"] = TEST_PUBLIC_KEY

# The models use PostgreSQL-specific types (JSONB, postgresql.UUID), so SQLite
# cannot compile the schema -- `db_session` needs a real Postgres.
# `docker compose up -d postgres` provides one with these credentials; override
# with TEST_DATABASE_URL (e.g. in CI).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://founderpilot:founderpilot_dev@127.0.0.1:5432/founderpilot_test",
)

# Imported here rather than at the top of the file: src.core.config reads the
# environment when it is first imported, and the block above is what sets it.
from stripe import SignatureVerificationError, StripeError  # noqa: E402

from src.models.billing import Plan, Subscription  # noqa: E402
from src.models.user import User  # noqa: E402
from src.schemas.slack import (  # noqa: E402
    EmailNotificationPayload,
    InvoiceNotificationPayload,
    MeetingNotificationPayload,
)


# =============================================================================
# Auth Fixtures (FEAT-001)
# =============================================================================

@pytest.fixture
def encryption_key() -> str:
    """Generate a fresh encryption key for tests."""
    return Fernet.generate_key().decode()


@pytest.fixture
def rsa_keys() -> tuple[str, str]:
    """Generate fresh RSA key pair for tests."""
    return generate_rsa_keys()


@pytest.fixture
def mock_redis() -> Generator[MagicMock, None, None]:
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.setex.return_value = True
    yield mock


# =============================================================================
# Database Fixtures
# =============================================================================

def _ensure_test_database() -> None:
    """Create the test database if it does not exist yet."""
    url = make_url(TEST_DATABASE_URL)
    if url.get_backend_name() != "postgresql" or not url.database:
        return
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def db_engine():
    """Engine bound to the test database, with the schema built once."""
    import src.models  # noqa: F401  - registers every model on Base.metadata
    from src.core.database import Base

    _ensure_test_database()
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Session on an empty database.

    The schema is built once per session (DDL is expensive); every test starts
    from empty tables. DELETE is used rather than TRUNCATE because TRUNCATE
    rewrites every table file, which dominates the runtime of the suite.
    """
    from src.core.database import Base

    with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())

    TestingSessionLocal = sessionmaker(bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def _reset_cached_redis():
    """Drop cached async Redis clients between tests.

    Both `src.api.dependencies` and the rate-limit middleware cache a client,
    and an async Redis connection belongs to the event loop that opened it.
    A server process has one loop for its lifetime so the cache is fine there;
    TestClient gives each test a fresh loop, so the cache has to go.
    """
    yield
    import src.api.dependencies as deps

    deps._redis_pool = None


@pytest.fixture
def async_db_session_factory(db_engine):
    """Async sessions against the same test database, for async endpoints.

    NullPool on purpose: TestClient runs each request batch on its own event
    loop, and a pooled asyncpg connection cannot cross loops.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    url = make_url(TEST_DATABASE_URL).set(drivername="postgresql+asyncpg")
    engine = create_async_engine(url, poolclass=NullPool)
    yield async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def override_async_db(async_db_session_factory):
    """Install an async `get_db` override on the app, and take it off after."""
    from src.api.dependencies import get_db
    from src.api.main import app

    async def _get_db():
        async with async_db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_db():
    """Mock database session (for unit tests without real DB)."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


# =============================================================================
# Common Fixtures
# =============================================================================

@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def user_id():
    """Generate a user ID for testing."""
    return uuid4()


# =============================================================================
# Tenant Fixtures
#
# A tenant IS a user (see src/models/user.py), and every tenant_id column is a
# real FK to users.id. Anything that writes a row keyed by tenant_id therefore
# needs the user to exist first -- hence `make_user` / `sample_user`.
# =============================================================================

@pytest.fixture
def make_user(db_session):
    """Factory creating persisted Users (each one is also a tenant)."""
    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        n = counter["n"]
        user = User(
            id=overrides.pop("id", uuid4()),
            email=overrides.pop("email", f"user{n}@example.com"),
            name=overrides.pop("name", f"Test User {n}"),
            google_id=overrides.pop("google_id", f"google-{uuid4()}"),
            onboarding_completed=overrides.pop("onboarding_completed", True),
            **overrides,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture
def sample_user(make_user):
    """A single persisted user/tenant."""
    return make_user()


@pytest.fixture
def tenant_id(sample_user):
    """Tenant id backed by a real users row."""
    return sample_user.id


# =============================================================================
# Billing Fixtures (FEAT-002)
# =============================================================================

@pytest.fixture
def sample_plan(db_session):
    """An active bundle plan. Its identity is the Stripe price id."""
    plan = Plan(
        stripe_price_id="price_bundle_test",
        stripe_product_id="prod_bundle_test",
        name="Bundle",
        description="All three agents",
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
    db_session.refresh(plan)
    return plan


@pytest.fixture
def sample_subscription(db_session, sample_user):
    """A trial subscription for `sample_user`."""
    now = datetime.utcnow()
    trial_ends = now + timedelta(days=14)
    subscription = Subscription(
        tenant_id=sample_user.id,
        stripe_customer_id="cus_test123",
        status="trial",
        trial_ends_at=trial_ends,
        current_period_start=now,
        current_period_end=trial_ends,
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription


@pytest.fixture
def mock_stripe():
    """Patch the Stripe calls BillingService makes.

    Keys match what the tests assert on: customer, checkout, portal.
    """
    with patch("src.services.billing_service.stripe") as mock:
        mock.Customer.create.return_value = MagicMock(id="cus_test123")
        mock.checkout.Session.create.return_value = MagicMock(
            url="https://checkout.stripe.com/test"
        )
        mock.billing_portal.Session.create.return_value = MagicMock(
            url="https://billing.stripe.com/test"
        )
        # Exception classes must stay real so `except stripe.StripeError` works.
        mock.StripeError = StripeError
        mock.SignatureVerificationError = SignatureVerificationError
        yield {
            "customer": mock.Customer.create,
            "checkout": mock.checkout.Session.create,
            "portal": mock.billing_portal.Session.create,
            "stripe": mock,
        }


# =============================================================================
# InboxPilot Fixtures (FEAT-003)
# =============================================================================

@pytest.fixture
def sample_email():
    """Parsed email payload (EmailData), as the InboxPilot nodes pass it around."""
    return {
        "message_id": "msg_12345",
        "thread_id": "thread_12345",
        "sender": "john@example.com",
        "sender_name": "John Doe",
        "subject": "Quick question about our meeting",
        "body": "Hi, could we move tomorrow's sync to 3pm? Thanks, John",
        "snippet": "Hi, could we move tomorrow's sync to 3pm?",
        "received_at": "2026-01-31T10:00:00Z",
        "thread_messages": [],
        "attachments": [],
        "labels": ["INBOX"],
    }


@pytest.fixture
def routine_classification():
    """ClassificationResult for a routine email.

    The category/suggested_action vocabulary is the one declared in
    src/agents/inbox_pilot/state.py.
    """
    return {
        "category": "routine",
        "confidence": 0.92,
        "reasoning": "Straightforward scheduling request from a known contact.",
        "suggested_action": "draft",
    }


# =============================================================================
# Slack Notification Payload Fixtures (FEAT-006)
# =============================================================================

@pytest.fixture
def sample_workflow_id():
    """Workflow id used by the Slack block builders."""
    return uuid4()


@pytest.fixture
def sample_email_payload(sample_workflow_id):
    """Payload for build_email_notification."""
    return EmailNotificationPayload(
        workflow_id=sample_workflow_id,
        sender="client@example.com",
        subject="Question about the invoice",
        classification="ROUTINE",
        confidence=92,
        proposed_response="Happy to confirm - invoice INV-42 is for $1,500.00.",
        email_snippet="Hi, could you confirm the amount on invoice INV-42?",
    )


@pytest.fixture
def sample_invoice_payload(sample_workflow_id):
    """Payload for build_invoice_notification (an overdue invoice)."""
    return InvoiceNotificationPayload(
        workflow_id=sample_workflow_id,
        client_name="Acme Inc.",
        invoice_number="INV-42",
        amount="$1,500.00",
        due_date="2026-01-15",
        days_overdue=16,
        proposed_action="Send reminder email",
    )


@pytest.fixture
def sample_meeting_payload(sample_workflow_id):
    """Payload for build_meeting_notification."""
    return MeetingNotificationPayload(
        workflow_id=sample_workflow_id,
        meeting_title="Quarterly review",
        start_time=datetime(2026, 2, 3, 10, 0, 0),
        attendees=["Alice Smith", "Bob Jones"],
        context_summary="Follow-up on the Q4 numbers.",
        proposed_prep="Re-read the Q4 report and the open action items.",
    )


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
