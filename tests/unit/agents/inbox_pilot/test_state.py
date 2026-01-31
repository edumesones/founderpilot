"""Tests for InboxPilot state definitions."""

import pytest
from src.agents.inbox_pilot.state import InboxState, EmailData, ClassificationResult


def test_email_data_structure(sample_email):
    """Test EmailData TypedDict structure."""
    assert sample_email["message_id"] == "msg_12345"
    assert sample_email["sender"] == "john@example.com"
    assert sample_email["subject"] == "Quick question about our meeting"
    assert isinstance(sample_email["thread_messages"], list)
    assert isinstance(sample_email["attachments"], list)


def test_classification_result_structure(routine_classification):
    """Test ClassificationResult TypedDict structure."""
    assert routine_classification["category"] == "routine"
    assert 0 <= routine_classification["confidence"] <= 1
    assert routine_classification["suggested_action"] in ["escalate", "draft", "archive", "ignore"]


def test_inbox_state_initialization():
    """Test InboxState can be initialized with required fields."""
    state: InboxState = {
        "message_id": "test_123",
        "user_id": "user_456",
        "config": None,
        "email": None,
        "classification": None,
        "draft": None,
        "needs_human_review": False,
        "human_decision": None,
        "edited_content": None,
        "action_taken": None,
        "error": None,
        "trace_id": "trace_789",
        "steps": [],
    }

    assert state["message_id"] == "test_123"
    assert state["needs_human_review"] is False
    assert state["steps"] == []
