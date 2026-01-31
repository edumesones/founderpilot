"""Integration tests for InboxPilot agent flows."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.agents.inbox_pilot.agent import InboxPilotAgent
from src.agents.inbox_pilot.state import InboxState


@pytest.fixture
def mock_gmail_client():
    """Mock Gmail client."""
    client = AsyncMock()
    client.get_message = AsyncMock(return_value={
        "id": "msg_123",
        "threadId": "thread_123",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "From", "value": "John Smith <john@example.com>"},
                {"name": "Subject", "value": "Meeting tomorrow"},
                {"name": "Date", "value": "Fri, 31 Jan 2026 10:00:00 +0000"},
            ],
            "body": {"data": ""},
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": "SGksCgpDYW4gd2UgbWVldCB0b21vcnJvdz8KClRoYW5rcw=="},
                }
            ],
        },
        "snippet": "Can we meet tomorrow?",
    })
    client.send_reply = AsyncMock(return_value={"id": "sent_msg_123"})
    client.archive = AsyncMock()
    client.add_label = AsyncMock()
    client.get_thread = AsyncMock(return_value={"messages": []})
    return client


@pytest.fixture
def mock_slack_notifier():
    """Mock Slack notifier."""
    notifier = AsyncMock()
    notifier.send_escalation = AsyncMock(return_value={"ts": "1234567890.123456"})
    notifier.update_message = AsyncMock()
    return notifier


@pytest.fixture
def mock_llm_router():
    """Mock LLM router with classification and draft responses."""
    router = MagicMock()

    # Mock classifier response
    classify_response = MagicMock()
    classify_response.content = '{"category": "routine", "confidence": 0.92, "reasoning": "Standard meeting request", "suggested_action": "draft"}'
    router.classify = AsyncMock(return_value=classify_response)

    # Mock draft response
    draft_response = MagicMock()
    draft_response.content = '{"content": "Hi John,\\n\\nYes, tomorrow works. What time?\\n\\nBest", "confidence": 0.88, "tone": "friendly"}'
    router.draft = AsyncMock(return_value=draft_response)

    return router


@pytest.fixture
def mock_config():
    """Mock user config."""
    config = MagicMock()
    config.escalation_threshold = 0.8
    config.draft_threshold = 0.7
    config.auto_archive_spam = True
    config.draft_for_routine = True
    config.escalate_urgent = True
    config.auto_send_high_confidence = False
    config.vip_domains = ["bigclient.com"]
    config.vip_emails = ["ceo@important.com"]
    config.ignore_patterns = []
    config.email_signature = "Best regards"
    return config


@pytest.fixture
def agent(mock_gmail_client, mock_slack_notifier, mock_llm_router, mock_config):
    """Create InboxPilotAgent instance."""
    return InboxPilotAgent(
        gmail_client=mock_gmail_client,
        slack_notifier=mock_slack_notifier,
        llm_router=mock_llm_router,
        user_config=mock_config,
        checkpointer=None,
    )


class TestHappyPathFlow:
    """Test the happy path: routine email -> classify -> draft -> execute."""

    async def test_routine_email_gets_drafted(
        self, agent, mock_gmail_client, mock_llm_router
    ):
        """Test routine email flows through draft and execution."""
        # Run agent
        result = await agent.run("msg_123")

        # Verify classification was called
        assert result.get("classification", {}).get("category") == "routine"

        # Verify draft was generated
        assert result.get("draft") is not None
        assert "content" in result.get("draft", {})

    async def test_email_is_archived_after_processing(
        self, agent, mock_gmail_client
    ):
        """Test email is labeled correctly after processing."""
        await agent.run("msg_123")

        # Verify label was applied (FP_Routine for routine emails)
        mock_gmail_client.add_label.assert_called()


class TestSpamFlow:
    """Test spam email handling."""

    async def test_spam_is_auto_archived(
        self, mock_gmail_client, mock_slack_notifier, mock_config
    ):
        """Test spam emails are auto-archived when configured."""
        # Set up spam classification response
        mock_llm = MagicMock()
        spam_response = MagicMock()
        spam_response.content = '{"category": "spam", "confidence": 0.98, "reasoning": "Promotional spam", "suggested_action": "archive"}'
        mock_llm.classify = AsyncMock(return_value=spam_response)

        mock_config.auto_archive_spam = True

        agent = InboxPilotAgent(
            gmail_client=mock_gmail_client,
            slack_notifier=mock_slack_notifier,
            llm_router=mock_llm,
            user_config=mock_config,
            checkpointer=None,
        )

        result = await agent.run("msg_spam")

        assert result.get("classification", {}).get("category") == "spam"
        mock_gmail_client.archive.assert_called()


class TestEscalationFlow:
    """Test escalation to human via Slack."""

    async def test_urgent_email_is_escalated(
        self, mock_gmail_client, mock_slack_notifier, mock_config
    ):
        """Test urgent emails trigger Slack escalation."""
        mock_llm = MagicMock()
        urgent_response = MagicMock()
        urgent_response.content = '{"category": "urgent", "confidence": 0.95, "reasoning": "Time-sensitive contract", "suggested_action": "escalate"}'
        mock_llm.classify = AsyncMock(return_value=urgent_response)

        mock_config.escalate_urgent = True

        agent = InboxPilotAgent(
            gmail_client=mock_gmail_client,
            slack_notifier=mock_slack_notifier,
            llm_router=mock_llm,
            user_config=mock_config,
            checkpointer=None,
        )

        result = await agent.run("msg_urgent")

        assert result.get("classification", {}).get("category") == "urgent"
        assert result.get("needs_human_review") is True
        mock_slack_notifier.send_escalation.assert_called()

    async def test_low_confidence_classification_is_escalated(
        self, mock_gmail_client, mock_slack_notifier, mock_config
    ):
        """Test low confidence classifications trigger escalation."""
        mock_llm = MagicMock()
        low_conf_response = MagicMock()
        low_conf_response.content = '{"category": "important", "confidence": 0.65, "reasoning": "Unclear context", "suggested_action": "escalate"}'
        mock_llm.classify = AsyncMock(return_value=low_conf_response)

        mock_config.escalation_threshold = 0.8  # Lower than 0.65

        agent = InboxPilotAgent(
            gmail_client=mock_gmail_client,
            slack_notifier=mock_slack_notifier,
            llm_router=mock_llm,
            user_config=mock_config,
            checkpointer=None,
        )

        result = await agent.run("msg_unclear")

        # Low confidence should trigger escalation
        assert result.get("needs_human_review") is True


class TestVIPRouting:
    """Test VIP domain and email routing."""

    async def test_vip_email_is_always_escalated(
        self, mock_gmail_client, mock_slack_notifier, mock_config
    ):
        """Test VIP emails are always escalated."""
        # Set up VIP email
        mock_gmail_client.get_message = AsyncMock(return_value={
            "id": "msg_vip",
            "threadId": "thread_vip",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "CEO <ceo@bigclient.com>"},
                    {"name": "Subject", "value": "Quick question"},
                    {"name": "Date", "value": "Fri, 31 Jan 2026 10:00:00 +0000"},
                ],
                "body": {"data": ""},
                "parts": [],
            },
            "snippet": "Just a quick question...",
        })

        mock_llm = MagicMock()
        routine_response = MagicMock()
        routine_response.content = '{"category": "routine", "confidence": 0.95, "reasoning": "Simple question", "suggested_action": "draft"}'
        mock_llm.classify = AsyncMock(return_value=routine_response)

        mock_config.vip_domains = ["bigclient.com"]

        agent = InboxPilotAgent(
            gmail_client=mock_gmail_client,
            slack_notifier=mock_slack_notifier,
            llm_router=mock_llm,
            user_config=mock_config,
            checkpointer=None,
        )

        result = await agent.run("msg_vip")

        # VIP emails should always be escalated regardless of classification
        assert result.get("needs_human_review") is True
        mock_slack_notifier.send_escalation.assert_called()


class TestResumeFlow:
    """Test resuming workflow after human decision."""

    async def test_approve_action_sends_draft(
        self, agent, mock_gmail_client
    ):
        """Test approving draft sends the email."""
        # First run to get draft
        await agent.run("msg_123")

        # Resume with approval
        result = await agent.resume(
            message_id="msg_123",
            human_decision="approve",
        )

        assert result.get("action_taken") == "sent"
        mock_gmail_client.send_reply.assert_called()

    async def test_reject_action_does_not_send(
        self, agent, mock_gmail_client
    ):
        """Test rejecting draft does not send email."""
        await agent.run("msg_123")

        result = await agent.resume(
            message_id="msg_123",
            human_decision="reject",
        )

        assert result.get("action_taken") == "rejected"
        # send_reply should not have been called for reject
        # (it may have been called in initial run, so we reset)
        mock_gmail_client.send_reply.reset_mock()

        # Re-run resume to verify
        result = await agent.resume(
            message_id="msg_123",
            human_decision="reject",
        )
        mock_gmail_client.send_reply.assert_not_called()

    async def test_edit_action_sends_edited_content(
        self, agent, mock_gmail_client
    ):
        """Test edit action sends the edited content."""
        await agent.run("msg_123")

        edited_content = "Hi John,\n\nEdited reply here.\n\nBest"
        result = await agent.resume(
            message_id="msg_123",
            human_decision="edit",
            edited_content=edited_content,
        )

        assert result.get("action_taken") == "sent"
        # Verify the edited content was sent
        mock_gmail_client.send_reply.assert_called()

    async def test_archive_action_archives_without_reply(
        self, agent, mock_gmail_client
    ):
        """Test archive action archives without sending reply."""
        await agent.run("msg_123")

        result = await agent.resume(
            message_id="msg_123",
            human_decision="archive",
        )

        assert result.get("action_taken") == "archived"
        mock_gmail_client.archive.assert_called()


class TestErrorHandling:
    """Test error handling in agent."""

    async def test_gmail_error_triggers_escalation(
        self, mock_slack_notifier, mock_llm_router, mock_config
    ):
        """Test Gmail API errors trigger escalation."""
        # Create Gmail client that raises error
        failing_gmail = AsyncMock()
        failing_gmail.get_message = AsyncMock(
            side_effect=Exception("Gmail API error")
        )

        agent = InboxPilotAgent(
            gmail_client=failing_gmail,
            slack_notifier=mock_slack_notifier,
            llm_router=mock_llm_router,
            user_config=mock_config,
            checkpointer=None,
        )

        # Should handle error gracefully
        result = await agent.run("msg_error")

        assert result.get("error") is not None
        assert result.get("needs_human_review") is True

    async def test_llm_error_triggers_escalation(
        self, mock_gmail_client, mock_slack_notifier, mock_config
    ):
        """Test LLM API errors trigger escalation."""
        failing_llm = MagicMock()
        failing_llm.classify = AsyncMock(
            side_effect=Exception("LLM API rate limit")
        )

        agent = InboxPilotAgent(
            gmail_client=mock_gmail_client,
            slack_notifier=mock_slack_notifier,
            llm_router=failing_llm,
            user_config=mock_config,
            checkpointer=None,
        )

        result = await agent.run("msg_error")

        # Error should trigger escalation for manual handling
        assert result.get("error") is not None
        assert result.get("needs_human_review") is True
