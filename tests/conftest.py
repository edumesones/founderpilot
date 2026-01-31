"""Pytest fixtures and configuration."""
import os
import pytest
from unittest.mock import MagicMock, patch
from uuid import UUID

# Set test environment
os.environ["DATABASE_URL"] = "postgresql://localhost/founderpilot_test"
os.environ["ENCRYPTION_KEY"] = "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlcw=="  # Test key


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


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
    """Sample invoice notification payload."""
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
    from datetime import datetime
    from src.schemas.slack import MeetingNotificationPayload

    return MeetingNotificationPayload(
        workflow_id=sample_workflow_id,
        meeting_title="Q1 Planning Session",
        start_time=datetime(2026, 2, 1, 10, 0),
        attendees=["Alice", "Bob", "Charlie"],
        context_summary="This is a quarterly planning meeting with the leadership team.",
        proposed_prep="Review Q4 metrics, prepare 3 key initiatives for Q1.",
    )
