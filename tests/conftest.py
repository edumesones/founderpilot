"""Pytest configuration and shared fixtures."""

import pytest
from uuid import uuid4

from src.agents.inbox_pilot.state import EmailData, ClassificationResult, DraftResult


@pytest.fixture
def sample_email() -> EmailData:
    """Sample email for testing."""
    return {
        "message_id": "msg_12345",
        "thread_id": "thread_12345",
        "sender": "john@example.com",
        "sender_name": "John Smith",
        "subject": "Quick question about our meeting",
        "body": "Hi,\n\nCould we reschedule our meeting to tomorrow?\n\nThanks,\nJohn",
        "snippet": "Could we reschedule our meeting to tomorrow?",
        "received_at": "2026-01-31T10:00:00Z",
        "thread_messages": [],
        "attachments": [],
        "labels": ["INBOX", "UNREAD"],
    }


@pytest.fixture
def urgent_email() -> EmailData:
    """Urgent email for testing."""
    return {
        "message_id": "msg_urgent",
        "thread_id": "thread_urgent",
        "sender": "ceo@bigclient.com",
        "sender_name": "Big Client CEO",
        "subject": "URGENT: Contract needs signature by EOD",
        "body": "We need the signed contract by end of day or we'll have to go with another vendor.",
        "snippet": "We need the signed contract by end of day",
        "received_at": "2026-01-31T10:00:00Z",
        "thread_messages": [],
        "attachments": [{"filename": "contract.pdf", "mimeType": "application/pdf", "size": 1024}],
        "labels": ["INBOX", "IMPORTANT"],
    }


@pytest.fixture
def spam_email() -> EmailData:
    """Spam email for testing."""
    return {
        "message_id": "msg_spam",
        "thread_id": "thread_spam",
        "sender": "noreply@marketing.spam.com",
        "sender_name": None,
        "subject": "You've won a FREE iPhone!!! Click here!!!",
        "body": "Congratulations! You've been selected for our exclusive offer...",
        "snippet": "Congratulations! You've been selected",
        "received_at": "2026-01-31T10:00:00Z",
        "thread_messages": [],
        "attachments": [],
        "labels": ["INBOX"],
    }


@pytest.fixture
def routine_classification() -> ClassificationResult:
    """Sample routine classification."""
    return {
        "category": "routine",
        "confidence": 0.92,
        "reasoning": "Standard meeting reschedule request",
        "suggested_action": "draft",
    }


@pytest.fixture
def urgent_classification() -> ClassificationResult:
    """Sample urgent classification."""
    return {
        "category": "urgent",
        "confidence": 0.95,
        "reasoning": "Time-sensitive contract deadline from important client",
        "suggested_action": "escalate",
    }


@pytest.fixture
def sample_draft() -> DraftResult:
    """Sample draft response."""
    return {
        "content": "Hi John,\n\nYes, tomorrow works for me. What time would be best for you?\n\nBest regards",
        "confidence": 0.88,
        "tone": "friendly",
    }


@pytest.fixture
def user_id():
    """Generate a user ID for testing."""
    return uuid4()


@pytest.fixture
def mock_user_config():
    """Mock InboxPilotConfig for testing."""
    return {
        "escalation_threshold": 0.8,
        "draft_threshold": 0.7,
        "auto_archive_spam": True,
        "draft_for_routine": True,
        "escalate_urgent": True,
        "auto_send_high_confidence": False,
        "vip_domains": ["bigclient.com"],
        "vip_emails": ["ceo@important.com"],
    }
