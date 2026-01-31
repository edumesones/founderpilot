"""Slack notification service for InboxPilot."""

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from src.core.config import settings


class SlackNotifier:
    """Send notifications and handle actions via Slack."""

    def __init__(self, bot_token: str | None = None):
        """Initialize Slack client.

        Args:
            bot_token: Slack bot token (defaults to settings)
        """
        self.client = AsyncWebClient(token=bot_token or settings.slack_bot_token)

    async def send_email_notification(
        self,
        user_id: str,
        email_data: dict,
        classification: dict,
        draft_content: str | None = None,
        error_message: str | None = None,
    ) -> dict:
        """Send email notification to user via Slack DM.

        Args:
            user_id: Internal user ID (used to look up Slack user)
            email_data: Email metadata (sender, subject, etc.)
            classification: Classification result
            draft_content: Draft response if available
            error_message: Error message if processing failed

        Returns:
            Slack API response
        """
        # TODO: Look up Slack user ID from our user_id
        # For now, we'll need the slack_user_id to be passed
        slack_user_id = email_data.get("slack_user_id") or user_id

        # Build the message blocks
        blocks = self._build_notification_blocks(
            email_data=email_data,
            classification=classification,
            draft_content=draft_content,
            error_message=error_message,
        )

        try:
            response = await self.client.chat_postMessage(
                channel=slack_user_id,  # DM to user
                text=f"New email from {email_data.get('sender', 'Unknown')}: {email_data.get('subject', 'No subject')}",
                blocks=blocks,
            )
            return response.data

        except SlackApiError as e:
            raise Exception(f"Failed to send Slack notification: {e.response['error']}")

    def _build_notification_blocks(
        self,
        email_data: dict,
        classification: dict,
        draft_content: str | None = None,
        error_message: str | None = None,
    ) -> list[dict]:
        """Build Slack Block Kit message for email notification."""
        blocks = []

        # Header
        category = classification.get("category", "unknown").upper()
        confidence = classification.get("confidence", 0)
        confidence_pct = f"{confidence:.0%}"

        emoji = {
            "urgent": ":rotating_light:",
            "important": ":star:",
            "routine": ":memo:",
            "spam": ":wastebasket:",
        }.get(classification.get("category", ""), ":email:")

        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {category} Email ({confidence_pct} confidence)",
                "emoji": True,
            },
        })

        # Email details
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*From:*\n{email_data.get('sender_name') or email_data.get('sender', 'Unknown')}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Received:*\n{email_data.get('received_at', 'Unknown')}",
                },
            ],
        })

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Subject:* {email_data.get('subject', 'No subject')}",
            },
        })

        # Snippet
        if email_data.get("snippet"):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{email_data['snippet'][:200]}...```",
                },
            })

        # Classification reasoning
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":brain: *Why:* {classification.get('reasoning', 'N/A')}",
                },
            ],
        })

        blocks.append({"type": "divider"})

        # Draft preview (if available)
        if draft_content:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*:pencil: Suggested Response:*",
                },
            })
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{draft_content[:500]}{'...' if len(draft_content) > 500 else ''}```",
                },
            })
            blocks.append({"type": "divider"})

        # Error message (if any)
        if error_message:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":warning: *Processing Error:* {error_message}",
                },
            })
            blocks.append({"type": "divider"})

        # Action buttons
        message_id = email_data.get("message_id", "")
        action_elements = []

        if draft_content:
            action_elements.extend([
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":white_check_mark: Send", "emoji": True},
                    "style": "primary",
                    "action_id": "inbox_pilot_approve",
                    "value": message_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":pencil2: Edit", "emoji": True},
                    "action_id": "inbox_pilot_edit",
                    "value": message_id,
                },
            ])

        action_elements.extend([
            {
                "type": "button",
                "text": {"type": "plain_text", "text": ":file_folder: Archive", "emoji": True},
                "action_id": "inbox_pilot_archive",
                "value": message_id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": ":x: Reject", "emoji": True},
                "style": "danger",
                "action_id": "inbox_pilot_reject",
                "value": message_id,
            },
        ])

        blocks.append({
            "type": "actions",
            "elements": action_elements,
        })

        return blocks

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: list[dict] | None = None,
    ) -> dict:
        """Update an existing Slack message.

        Args:
            channel: Channel ID
            ts: Message timestamp
            text: New message text
            blocks: New message blocks

        Returns:
            Slack API response
        """
        response = await self.client.chat_update(
            channel=channel,
            ts=ts,
            text=text,
            blocks=blocks,
        )
        return response.data

    async def open_edit_modal(
        self,
        trigger_id: str,
        message_id: str,
        current_draft: str,
    ) -> dict:
        """Open a modal for editing the draft response.

        Args:
            trigger_id: Slack trigger ID from interaction
            message_id: Email message ID
            current_draft: Current draft content

        Returns:
            Slack API response
        """
        response = await self.client.views_open(
            trigger_id=trigger_id,
            view={
                "type": "modal",
                "callback_id": "inbox_pilot_edit_modal",
                "private_metadata": message_id,
                "title": {"type": "plain_text", "text": "Edit Response"},
                "submit": {"type": "plain_text", "text": "Send"},
                "close": {"type": "plain_text", "text": "Cancel"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "draft_input",
                        "label": {"type": "plain_text", "text": "Your Response"},
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "draft_content",
                            "multiline": True,
                            "initial_value": current_draft,
                        },
                    },
                ],
            },
        )
        return response.data
