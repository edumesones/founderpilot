"""Tests for email classification."""

import pytest
from src.agents.inbox_pilot.prompts.classify import (
    build_classification_prompt,
    CLASSIFICATION_SYSTEM_PROMPT,
)


def test_classification_system_prompt_contains_categories():
    """Test system prompt includes all categories."""
    assert "URGENT" in CLASSIFICATION_SYSTEM_PROMPT
    assert "IMPORTANT" in CLASSIFICATION_SYSTEM_PROMPT
    assert "ROUTINE" in CLASSIFICATION_SYSTEM_PROMPT
    assert "SPAM" in CLASSIFICATION_SYSTEM_PROMPT


def test_classification_system_prompt_contains_output_format():
    """Test system prompt specifies JSON output."""
    assert "JSON" in CLASSIFICATION_SYSTEM_PROMPT
    assert '"category"' in CLASSIFICATION_SYSTEM_PROMPT
    assert '"confidence"' in CLASSIFICATION_SYSTEM_PROMPT


def test_build_classification_prompt_includes_email_details(sample_email):
    """Test prompt builder includes all email fields."""
    prompt = build_classification_prompt(sample_email)

    assert sample_email["sender"] in prompt
    assert sample_email["subject"] in prompt
    assert sample_email["body"] in prompt


def test_build_classification_prompt_includes_thread_context():
    """Test prompt includes thread context when available."""
    email = {
        "message_id": "msg_1",
        "thread_id": "thread_1",
        "sender": "test@example.com",
        "sender_name": "Test User",
        "subject": "Re: Original Subject",
        "body": "Reply body",
        "snippet": "Reply snippet",
        "received_at": "2026-01-31T10:00:00Z",
        "thread_messages": [
            {"sender": "original@example.com", "subject": "Original Subject", "snippet": "Original message"}
        ],
        "attachments": [],
        "labels": [],
    }

    prompt = build_classification_prompt(email)

    assert "Previous Messages" in prompt
    assert "original@example.com" in prompt


def test_build_classification_prompt_truncates_long_body():
    """Test prompt truncates very long email bodies."""
    email = {
        "message_id": "msg_1",
        "thread_id": "thread_1",
        "sender": "test@example.com",
        "sender_name": None,
        "subject": "Long email",
        "body": "x" * 5000,  # 5000 chars
        "snippet": "Long email",
        "received_at": "2026-01-31T10:00:00Z",
        "thread_messages": [],
        "attachments": [],
        "labels": [],
    }

    prompt = build_classification_prompt(email)

    # Should be truncated to ~2000 chars
    assert len(prompt) < 3500
    assert "truncated" in prompt
