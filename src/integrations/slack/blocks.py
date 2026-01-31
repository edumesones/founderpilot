"""Block Kit message templates for Slack notifications."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.schemas.slack import (
    EmailNotificationPayload,
    InvoiceNotificationPayload,
    MeetingNotificationPayload,
    ActionResult,
)


def build_email_notification(payload: EmailNotificationPayload) -> list:
    """
    Build Block Kit blocks for an email action notification.

    Shows email details, classification, proposed response, and action buttons.
    """
    confidence_emoji = _get_confidence_emoji(payload.confidence)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Email Action Required",
                "emoji": True,
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*From:*\n{payload.sender}"},
                {"type": "mrkdwn", "text": f"*Subject:*\n{payload.subject}"},
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{confidence_emoji} Classification: *{payload.classification}* ({payload.confidence}% confidence)"
                }
            ]
        },
        {"type": "divider"},
    ]

    # Add email snippet if provided
    if payload.email_snippet:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Email Preview:*\n>{payload.email_snippet[:300]}..."
            }
        })

    # Add proposed response
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Proposed Response:*\n```{payload.proposed_response[:1500]}```"
        }
    })

    # Add action buttons
    blocks.append(_build_action_buttons(str(payload.workflow_id)))

    return blocks


def build_invoice_notification(payload: InvoiceNotificationPayload) -> list:
    """
    Build Block Kit blocks for an invoice reminder notification.

    Shows invoice details and proposed action.
    """
    urgency_text = ""
    if payload.days_overdue and payload.days_overdue > 0:
        urgency_text = f" :warning: *{payload.days_overdue} days overdue*"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Invoice Follow-up Required",
                "emoji": True,
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Client:*\n{payload.client_name}"},
                {"type": "mrkdwn", "text": f"*Invoice:*\n{payload.invoice_number}"},
                {"type": "mrkdwn", "text": f"*Amount:*\n{payload.amount}"},
                {"type": "mrkdwn", "text": f"*Due Date:*\n{payload.due_date}{urgency_text}"},
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Proposed Action:*\n{payload.proposed_action}"
            }
        },
        _build_action_buttons(str(payload.workflow_id)),
    ]

    return blocks


def build_meeting_notification(payload: MeetingNotificationPayload) -> list:
    """
    Build Block Kit blocks for a meeting prep notification.

    Shows meeting details, context summary, and prep suggestions.
    """
    time_str = payload.start_time.strftime("%I:%M %p")
    date_str = payload.start_time.strftime("%A, %B %d")
    attendees_str = ", ".join(payload.attendees[:5])
    if len(payload.attendees) > 5:
        attendees_str += f" +{len(payload.attendees) - 5} more"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Meeting Prep Ready",
                "emoji": True,
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Meeting:*\n{payload.meeting_title}"},
                {"type": "mrkdwn", "text": f"*When:*\n{date_str} at {time_str}"},
            ]
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Attendees:* {attendees_str}"}
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Context Summary:*\n{payload.context_summary}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Suggested Prep:*\n{payload.proposed_prep}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Got it!", "emoji": True},
                    "style": "primary",
                    "action_id": "acknowledge_action",
                    "value": str(payload.workflow_id),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Snooze 30min", "emoji": True},
                    "action_id": "snooze_action",
                    "value": str(payload.workflow_id),
                },
            ]
        },
    ]

    return blocks


def build_success_blocks(result: ActionResult) -> list:
    """
    Build Block Kit blocks for action confirmation.

    Replaces the original message after user takes action.
    """
    action_emoji = {
        "approve": "white_check_mark",
        "reject": "x",
        "edit": "pencil2",
        "snooze": "alarm_clock",
        "acknowledge": "thumbsup",
    }.get(result.action, "heavy_check_mark")

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":{action_emoji}: *Action completed*\n{result.summary}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Processed at {result.timestamp.strftime('%I:%M %p')}"
                }
            ]
        },
    ]


def build_error_blocks(error_message: str) -> list:
    """Build Block Kit blocks for error display."""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":warning: *Error*\n{error_message}"
            }
        },
    ]


def build_edit_modal(
    workflow_id: UUID,
    current_content: str,
    title: str = "Edit Response",
) -> dict:
    """
    Build a modal for editing proposed content.

    Used when user clicks "Edit" button.
    """
    return {
        "type": "modal",
        "callback_id": "edit_modal_submit",
        "private_metadata": str(workflow_id),
        "title": {"type": "plain_text", "text": title[:24]},  # Max 24 chars
        "submit": {"type": "plain_text", "text": "Send"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "edit_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "edit_input",
                    "multiline": True,
                    "initial_value": current_content,
                    "max_length": 3000,
                },
                "label": {"type": "plain_text", "text": "Response"},
            }
        ],
    }


def build_welcome_message(team_name: str) -> list:
    """
    Build welcome message sent after successful Slack installation.
    """
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Welcome to FounderPilot!",
                "emoji": True,
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{team_name}* is now connected. :tada:\n\n"
                    "I'll send you notifications when your AI agents need your input:\n"
                    "- Email drafts that need approval\n"
                    "- Invoice reminders to review\n"
                    "- Meeting prep summaries\n\n"
                    "You can approve, reject, or edit directly from Slack."
                )
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "You can disconnect anytime from your FounderPilot dashboard."
                }
            ]
        },
    ]


def build_expired_action_blocks(workflow_id: str) -> list:
    """Build blocks shown when an action has expired (>24h)."""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":hourglass: *Action Expired*\nThis action is no longer available. Please check your dashboard for current items."
            }
        },
    ]


def _build_action_buttons(workflow_id: str) -> dict:
    """Build standard action buttons for notifications."""
    return {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve", "emoji": True},
                "style": "primary",
                "action_id": "approve_action",
                "value": workflow_id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Edit", "emoji": True},
                "action_id": "edit_action",
                "value": workflow_id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Snooze", "emoji": True},
                "action_id": "snooze_action",
                "value": workflow_id,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Reject", "emoji": True},
                "style": "danger",
                "action_id": "reject_action",
                "value": workflow_id,
            },
        ]
    }


def _get_confidence_emoji(confidence: int) -> str:
    """Get emoji based on confidence level."""
    if confidence >= 90:
        return ":green_circle:"
    elif confidence >= 70:
        return ":large_yellow_circle:"
    else:
        return ":red_circle:"
