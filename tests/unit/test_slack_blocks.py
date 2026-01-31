"""Unit tests for Slack Block Kit templates."""
import pytest
from datetime import datetime
from uuid import UUID

from src.integrations.slack.blocks import (
    build_email_notification,
    build_invoice_notification,
    build_meeting_notification,
    build_success_blocks,
    build_edit_modal,
    build_welcome_message,
)
from src.schemas.slack import ActionResult


class TestEmailNotification:
    """Tests for email notification blocks."""

    def test_build_email_notification_basic(self, sample_email_payload):
        """Test basic email notification structure."""
        blocks = build_email_notification(sample_email_payload)

        assert isinstance(blocks, list)
        assert len(blocks) > 0

        # Check header
        header = blocks[0]
        assert header["type"] == "header"
        assert "Email" in header["text"]["text"]

    def test_build_email_notification_has_sender_subject(self, sample_email_payload):
        """Test that sender and subject are included."""
        blocks = build_email_notification(sample_email_payload)

        # Find section with fields
        section_blocks = [b for b in blocks if b.get("type") == "section"]
        assert len(section_blocks) > 0

        # Check for sender and subject in fields
        all_text = str(blocks)
        assert sample_email_payload.sender in all_text
        assert sample_email_payload.subject in all_text

    def test_build_email_notification_has_action_buttons(self, sample_email_payload):
        """Test that action buttons are present."""
        blocks = build_email_notification(sample_email_payload)

        # Find actions block
        actions_blocks = [b for b in blocks if b.get("type") == "actions"]
        assert len(actions_blocks) == 1

        actions = actions_blocks[0]
        button_ids = [e.get("action_id") for e in actions.get("elements", [])]

        assert "approve_action" in button_ids
        assert "reject_action" in button_ids
        assert "edit_action" in button_ids
        assert "snooze_action" in button_ids

    def test_build_email_notification_includes_workflow_id(self, sample_email_payload):
        """Test that workflow ID is in button values."""
        blocks = build_email_notification(sample_email_payload)

        actions_block = [b for b in blocks if b.get("type") == "actions"][0]
        button_values = [e.get("value") for e in actions_block.get("elements", [])]

        assert str(sample_email_payload.workflow_id) in button_values


class TestInvoiceNotification:
    """Tests for invoice notification blocks."""

    def test_build_invoice_notification_basic(self, sample_invoice_payload):
        """Test basic invoice notification structure."""
        blocks = build_invoice_notification(sample_invoice_payload)

        assert isinstance(blocks, list)
        assert len(blocks) > 0

        # Check header
        header = blocks[0]
        assert header["type"] == "header"
        assert "Invoice" in header["text"]["text"]

    def test_build_invoice_notification_shows_overdue(self, sample_invoice_payload):
        """Test that overdue status is shown."""
        blocks = build_invoice_notification(sample_invoice_payload)
        all_text = str(blocks)

        assert "overdue" in all_text.lower()


class TestMeetingNotification:
    """Tests for meeting notification blocks."""

    def test_build_meeting_notification_basic(self, sample_meeting_payload):
        """Test basic meeting notification structure."""
        blocks = build_meeting_notification(sample_meeting_payload)

        assert isinstance(blocks, list)
        assert len(blocks) > 0

        # Check header
        header = blocks[0]
        assert header["type"] == "header"
        assert "Meeting" in header["text"]["text"]

    def test_build_meeting_notification_has_attendees(self, sample_meeting_payload):
        """Test that attendees are shown."""
        blocks = build_meeting_notification(sample_meeting_payload)
        all_text = str(blocks)

        assert "Alice" in all_text
        assert "Bob" in all_text


class TestSuccessBlocks:
    """Tests for success confirmation blocks."""

    def test_build_success_blocks_approve(self, sample_workflow_id):
        """Test success blocks for approve action."""
        result = ActionResult(
            success=True,
            workflow_id=sample_workflow_id,
            action="approve",
            summary="Email sent successfully.",
            timestamp=datetime.utcnow(),
        )

        blocks = build_success_blocks(result)

        assert isinstance(blocks, list)
        assert len(blocks) > 0

        # Check contains success indicator
        all_text = str(blocks)
        assert "completed" in all_text.lower()
        assert result.summary in all_text


class TestEditModal:
    """Tests for edit modal."""

    def test_build_edit_modal_structure(self, sample_workflow_id):
        """Test edit modal has correct structure."""
        content = "This is the content to edit."
        modal = build_edit_modal(
            workflow_id=sample_workflow_id,
            current_content=content,
        )

        assert modal["type"] == "modal"
        assert modal["callback_id"] == "edit_modal_submit"
        assert modal["private_metadata"] == str(sample_workflow_id)

        # Check has input block
        assert len(modal["blocks"]) > 0
        input_block = modal["blocks"][0]
        assert input_block["type"] == "input"
        assert input_block["element"]["initial_value"] == content


class TestWelcomeMessage:
    """Tests for welcome message."""

    def test_build_welcome_message(self):
        """Test welcome message structure."""
        blocks = build_welcome_message("Test Workspace")

        assert isinstance(blocks, list)
        assert len(blocks) > 0

        # Check header
        header = blocks[0]
        assert header["type"] == "header"
        assert "Welcome" in header["text"]["text"]

        # Check team name is included
        all_text = str(blocks)
        assert "Test Workspace" in all_text
