"""
Slack notification templates for InvoicePilot.

This module provides notification templates and builders for Slack messages
related to invoice detection, reminders, and escalations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal


def format_currency(amount: Decimal, currency: str) -> str:
    """Format amount with currency symbol."""
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "MXN": "$",
    }
    symbol = currency_symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def format_date(date: datetime) -> str:
    """Format date for display."""
    return date.strftime("%b %d, %Y")


def days_overdue(due_date: datetime) -> int:
    """Calculate days overdue from due date."""
    delta = datetime.utcnow() - due_date
    return max(0, delta.days)


def build_low_confidence_invoice_notification(
    invoice_data: Dict[str, Any],
    confidence: float,
    pdf_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build Slack notification for low confidence invoice detection.

    Args:
        invoice_data: Extracted invoice data
        confidence: Confidence score (0-1)
        pdf_url: URL to invoice PDF

    Returns:
        Slack message payload with blocks and attachments
    """
    invoice_number = invoice_data.get("invoice_number", "Unknown")
    client_name = invoice_data.get("client_name", "Unknown")
    client_email = invoice_data.get("client_email", "")
    amount = invoice_data.get("amount_total", 0)
    currency = invoice_data.get("currency", "USD")
    issue_date = invoice_data.get("issue_date")
    due_date = invoice_data.get("due_date")

    confidence_emoji = "⚠️" if confidence < 0.5 else "🟡"
    confidence_pct = f"{confidence * 100:.0f}%"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{confidence_emoji} Low Confidence Invoice Detected",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Invoice:* {invoice_number}\n"
                    f"*Client:* {client_name}\n"
                    f"*Email:* {client_email}\n"
                    f"*Amount:* {format_currency(Decimal(str(amount)), currency)}\n"
                    f"*Confidence:* {confidence_pct}"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Issue Date:* {format_date(issue_date) if issue_date else 'Unknown'}\n"
                    f"*Due Date:* {format_date(due_date) if due_date else 'Unknown'}"
                ),
            },
        },
        {
            "type": "divider",
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⚡ *Action Required:* Review and confirm invoice details",
                },
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Confirm Invoice",
                        "emoji": True,
                    },
                    "style": "primary",
                    "action_id": "confirm_invoice",
                    "value": invoice_data.get("id", ""),
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✏️ Edit & Confirm",
                        "emoji": True,
                    },
                    "action_id": "edit_invoice",
                    "value": invoice_data.get("id", ""),
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "❌ Reject",
                        "emoji": True,
                    },
                    "style": "danger",
                    "action_id": "reject_invoice",
                    "value": invoice_data.get("id", ""),
                },
            ],
        },
    ]

    # Add PDF link if available
    if pdf_url:
        blocks.insert(
            -2,  # Before divider
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📄 <{pdf_url}|View Invoice PDF>",
                },
            },
        )

    return {
        "text": f"Low confidence invoice detected: {invoice_number}",
        "blocks": blocks,
    }


def build_reminder_approval_notification(
    invoice_data: Dict[str, Any],
    reminder_data: Dict[str, Any],
    draft_message: str,
) -> Dict[str, Any]:
    """
    Build Slack notification for reminder approval.

    Args:
        invoice_data: Invoice details
        reminder_data: Reminder details
        draft_message: Draft reminder message

    Returns:
        Slack message payload with blocks and attachments
    """
    invoice_number = invoice_data.get("invoice_number", "Unknown")
    client_name = invoice_data.get("client_name", "Unknown")
    client_email = invoice_data.get("client_email", "")
    amount = invoice_data.get("amount_total", 0)
    amount_paid = invoice_data.get("amount_paid", 0)
    currency = invoice_data.get("currency", "USD")
    due_date = invoice_data.get("due_date")

    reminder_type = reminder_data.get("type", "gentle")
    reminder_id = reminder_data.get("id", "")

    overdue_days = days_overdue(due_date) if due_date else 0
    overdue_text = f"{overdue_days} days overdue" if overdue_days > 0 else "Due soon"

    remaining = Decimal(str(amount)) - Decimal(str(amount_paid))

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📬 Reminder Ready for Approval",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Invoice:* {invoice_number}\n"
                    f"*Client:* {client_name} ({client_email})\n"
                    f"*Amount Due:* {format_currency(remaining, currency)}\n"
                    f"*Status:* {overdue_text}\n"
                    f"*Reminder Type:* {reminder_type.title()}"
                ),
            },
        },
        {
            "type": "divider",
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Draft Message:*\n```{draft_message}```",
            },
        },
        {
            "type": "divider",
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⚡ *Action Required:* Approve, edit, or skip this reminder",
                },
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Approve & Send",
                        "emoji": True,
                    },
                    "style": "primary",
                    "action_id": "approve_reminder",
                    "value": reminder_id,
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✏️ Edit Message",
                        "emoji": True,
                    },
                    "action_id": "edit_reminder",
                    "value": reminder_id,
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⏭️ Skip This Reminder",
                        "emoji": True,
                    },
                    "action_id": "skip_reminder",
                    "value": reminder_id,
                },
            ],
        },
    ]

    return {
        "text": f"Reminder ready for approval: {invoice_number}",
        "blocks": blocks,
    }


def build_problem_pattern_escalation(
    invoice_data: Dict[str, Any],
    reminder_count: int,
    reminder_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build Slack notification for problem pattern escalation.

    Args:
        invoice_data: Invoice details
        reminder_count: Number of reminders sent
        reminder_history: List of reminder records

    Returns:
        Slack message payload with blocks and attachments
    """
    invoice_number = invoice_data.get("invoice_number", "Unknown")
    client_name = invoice_data.get("client_name", "Unknown")
    client_email = invoice_data.get("client_email", "")
    amount = invoice_data.get("amount_total", 0)
    amount_paid = invoice_data.get("amount_paid", 0)
    currency = invoice_data.get("currency", "USD")
    due_date = invoice_data.get("due_date")

    overdue_days = days_overdue(due_date) if due_date else 0
    remaining = Decimal(str(amount)) - Decimal(str(amount_paid))

    # Format reminder history
    history_text = ""
    for reminder in reminder_history[-3:]:  # Last 3 reminders
        sent_at = reminder.get("sent_at")
        reminder_type = reminder.get("type", "unknown")
        history_text += f"• {format_date(sent_at)} - {reminder_type.title()} reminder\n"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 Problem Pattern Detected",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Invoice:* {invoice_number}\n"
                    f"*Client:* {client_name} ({client_email})\n"
                    f"*Amount Due:* {format_currency(remaining, currency)}\n"
                    f"*Overdue:* {overdue_days} days\n"
                    f"*Reminders Sent:* {reminder_count} (no payment received)"
                ),
            },
        },
        {
            "type": "divider",
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recent Reminder History:*\n{history_text}",
            },
        },
        {
            "type": "divider",
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "⚠️ *This client may require direct intervention.* "
                        "Consider a phone call or escalation to collections."
                    ),
                },
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📞 Call Client",
                        "emoji": True,
                    },
                    "style": "primary",
                    "action_id": "call_client",
                    "value": invoice_data.get("id", ""),
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📧 Send Final Notice",
                        "emoji": True,
                    },
                    "action_id": "send_final_notice",
                    "value": invoice_data.get("id", ""),
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "💰 Mark as Paid",
                        "emoji": True,
                    },
                    "action_id": "mark_paid_from_escalation",
                    "value": invoice_data.get("id", ""),
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📝 Add Note",
                        "emoji": True,
                    },
                    "action_id": "add_note_to_invoice",
                    "value": invoice_data.get("id", ""),
                },
            ],
        },
    ]

    return {
        "text": f"Problem pattern detected for invoice {invoice_number}",
        "blocks": blocks,
    }


def build_invoice_paid_notification(
    invoice_data: Dict[str, Any],
    marked_by: str,
) -> Dict[str, Any]:
    """
    Build Slack notification for invoice marked as paid.

    Args:
        invoice_data: Invoice details
        marked_by: User who marked as paid

    Returns:
        Slack message payload
    """
    invoice_number = invoice_data.get("invoice_number", "Unknown")
    client_name = invoice_data.get("client_name", "Unknown")
    amount = invoice_data.get("amount_total", 0)
    currency = invoice_data.get("currency", "USD")

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"✅ *Invoice Marked as Paid*\n\n"
                    f"*Invoice:* {invoice_number}\n"
                    f"*Client:* {client_name}\n"
                    f"*Amount:* {format_currency(Decimal(str(amount)), currency)}\n"
                    f"*Marked by:* {marked_by}"
                ),
            },
        },
    ]

    return {
        "text": f"Invoice {invoice_number} marked as paid",
        "blocks": blocks,
    }


def build_reminder_sent_notification(
    invoice_data: Dict[str, Any],
    reminder_type: str,
) -> Dict[str, Any]:
    """
    Build Slack notification for reminder sent confirmation.

    Args:
        invoice_data: Invoice details
        reminder_type: Type of reminder sent

    Returns:
        Slack message payload
    """
    invoice_number = invoice_data.get("invoice_number", "Unknown")
    client_name = invoice_data.get("client_name", "Unknown")
    client_email = invoice_data.get("client_email", "")

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"📨 *Reminder Sent*\n\n"
                    f"*Invoice:* {invoice_number}\n"
                    f"*Client:* {client_name} ({client_email})\n"
                    f"*Type:* {reminder_type.title()}"
                ),
            },
        },
    ]

    return {
        "text": f"Reminder sent for invoice {invoice_number}",
        "blocks": blocks,
    }
