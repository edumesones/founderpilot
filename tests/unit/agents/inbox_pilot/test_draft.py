"""Tests for draft generation."""

import pytest
from src.agents.inbox_pilot.prompts.draft import (
    build_draft_prompt,
    DRAFT_SYSTEM_PROMPT,
)


def test_draft_system_prompt_contains_guidelines():
    """Test system prompt includes drafting guidelines."""
    assert "tone" in DRAFT_SYSTEM_PROMPT.lower()
    assert "brief" in DRAFT_SYSTEM_PROMPT.lower()
    assert "JSON" in DRAFT_SYSTEM_PROMPT


def test_draft_system_prompt_specifies_output_format():
    """Test system prompt specifies JSON output."""
    assert '"content"' in DRAFT_SYSTEM_PROMPT
    assert '"confidence"' in DRAFT_SYSTEM_PROMPT
    assert '"tone"' in DRAFT_SYSTEM_PROMPT


def test_build_draft_prompt_includes_email_and_classification(
    sample_email, routine_classification
):
    """Test prompt builder includes both email and classification."""
    prompt = build_draft_prompt(sample_email, routine_classification)

    # Email details
    assert sample_email["sender"] in prompt
    assert sample_email["subject"] in prompt

    # Classification details
    assert routine_classification["category"] in prompt
    assert routine_classification["reasoning"] in prompt


def test_build_draft_prompt_includes_signature_when_provided(
    sample_email, routine_classification
):
    """Test prompt includes email signature when provided."""
    signature = "Best regards,\nJohn Doe\nFounder, Acme Inc."

    prompt = build_draft_prompt(
        sample_email,
        routine_classification,
        signature=signature,
    )

    assert "Best regards" in prompt
    assert "John Doe" in prompt


def test_build_draft_prompt_without_signature(
    sample_email, routine_classification
):
    """Test prompt works without signature."""
    prompt = build_draft_prompt(
        sample_email,
        routine_classification,
        signature=None,
    )

    assert "Signature" not in prompt
    assert sample_email["body"] in prompt
