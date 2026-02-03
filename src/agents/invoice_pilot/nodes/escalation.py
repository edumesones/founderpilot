"""Escalation flow nodes for InvoicePilot agent."""

from datetime import datetime
from typing import Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.invoice_pilot.prompts.reminder import ESCALATION_NOTIFICATION_TEMPLATE
from src.agents.invoice_pilot.state import EscalationState
from src.integrations.slack.notifier import SlackNotifier
from src.models.invoice import Invoice, InvoiceReminder, InvoiceAction


async def detect_problem_pattern(
    state: EscalationState,
    db: AsyncSession,
) -> Dict:
    """Detect problem patterns in invoice payment history.

    Problem patterns include:
    - 3+ reminders sent without payment
    - Invoice overdue by 30+ days
    - Multiple invoices from same client overdue

    Args:
        state: Current escalation state
        db: Database session

    Returns:
        Updated state with problem pattern details
    """
    invoice_id = state["invoice_id"]
    tenant_id = state["tenant_id"]

    try:
        # Fetch invoice with reminders
        stmt = select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice:
            return {
                "error": f"Invoice {invoice_id} not found",
                "steps": state.get("steps", []) + [{
                    "node": "detect_problem_pattern",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": {"status": "not_found"},
                    "error": f"Invoice {invoice_id} not found",
                }],
            }

        # Get reminder history
        stmt = select(InvoiceReminder).where(
            InvoiceReminder.invoice_id == invoice_id,
            InvoiceReminder.status == "sent",
        ).order_by(InvoiceReminder.sent_at)
        result = await db.execute(stmt)
        reminders = result.scalars().all()

        # Calculate days overdue
        today = datetime.utcnow().date()
        due_date = invoice.due_date
        days_overdue = (today - due_date).days if due_date else 0

        # Check for problem patterns
        problem_detected = False
        pattern_type = None
        severity = "low"

        # Pattern 1: 3+ reminders without payment
        if len(reminders) >= 3 and invoice.status != "paid":
            problem_detected = True
            pattern_type = "repeated_reminders"
            severity = "high"

        # Pattern 2: 30+ days overdue
        elif days_overdue >= 30 and invoice.status != "paid":
            problem_detected = True
            pattern_type = "long_overdue"
            severity = "high"

        # Pattern 3: Multiple reminders + 14+ days overdue
        elif len(reminders) >= 2 and days_overdue >= 14:
            problem_detected = True
            pattern_type = "extended_delay"
            severity = "medium"

        # Build reminder history for notification
        reminder_history = [
            {
                "id": reminder.id,
                "sent_at": reminder.sent_at.isoformat() if reminder.sent_at else None,
                "type": reminder.type,
                "response_received": reminder.response_received,
            }
            for reminder in reminders
        ]

        # Check for other overdue invoices from same client
        stmt = select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.client_email == invoice.client_email,
            Invoice.status.in_(["sent", "overdue"]),
            Invoice.id != invoice_id,
        )
        result = await db.execute(stmt)
        other_overdue = result.scalars().all()

        if len(other_overdue) > 0:
            severity = "critical"
            pattern_type = "multiple_invoices_overdue"

        return {
            "invoice_data": {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "client_name": invoice.client_name,
                "client_email": invoice.client_email,
                "amount_total": float(invoice.amount_total),
                "currency": invoice.currency,
                "due_date": due_date.isoformat() if due_date else None,
                "status": invoice.status,
                "days_overdue": days_overdue,
            },
            "reminder_history": reminder_history,
            "pattern_type": pattern_type,
            "problem_detected": problem_detected,
            "severity": severity,
            "other_overdue_count": len(other_overdue),
            "steps": state.get("steps", []) + [{
                "node": "detect_problem_pattern",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {
                    "problem_detected": problem_detected,
                    "pattern_type": pattern_type,
                    "severity": severity,
                    "reminder_count": len(reminders),
                    "days_overdue": days_overdue,
                },
                "error": None,
            }],
        }

    except Exception as e:
        return {
            "error": f"Failed to detect problem pattern: {str(e)}",
            "steps": state.get("steps", []) + [{
                "node": "detect_problem_pattern",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "error"},
                "error": str(e),
            }],
        }


async def escalate_to_slack(
    state: EscalationState,
    slack: SlackNotifier,
    db: AsyncSession,
) -> Dict:
    """Send escalation notification to Slack.

    Args:
        state: Current escalation state with problem details
        slack: Slack notifier client
        db: Database session for audit trail

    Returns:
        Updated state with escalation status
    """
    invoice_data = state.get("invoice_data", {})
    pattern_type = state.get("pattern_type")
    problem_detected = state.get("problem_detected", False)
    severity = state.get("severity", "low")

    # Skip if no problem detected
    if not problem_detected:
        return {
            "escalated": False,
            "steps": state.get("steps", []) + [{
                "node": "escalate_to_slack",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "no_problem_detected"},
                "error": None,
            }],
        }

    if not invoice_data:
        return {
            "error": "No invoice data available for escalation",
            "steps": state.get("steps", []) + [{
                "node": "escalate_to_slack",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "no_invoice_data"},
                "error": "No invoice data",
            }],
        }

    try:
        # Build notification message
        reminder_count = len(state.get("reminder_history", []))
        days_overdue = invoice_data.get("days_overdue", 0)

        # Pattern type descriptions
        pattern_descriptions = {
            "repeated_reminders": f"{reminder_count} reminders sent without response",
            "long_overdue": f"{days_overdue} days overdue",
            "extended_delay": f"{reminder_count} reminders + {days_overdue} days overdue",
            "multiple_invoices_overdue": f"Multiple invoices overdue for this client",
        }

        message = ESCALATION_NOTIFICATION_TEMPLATE.format(
            invoice_number=invoice_data.get("invoice_number", "N/A"),
            client_name=invoice_data.get("client_name", "N/A"),
            currency=invoice_data.get("currency", "EUR"),
            amount=invoice_data.get("amount_total", 0),
            days_overdue=days_overdue,
            reminder_count=reminder_count,
            pattern_type=pattern_descriptions.get(pattern_type, pattern_type),
            invoice_url=f"/invoices/{invoice_data.get('id')}",
        )

        # Add severity emoji
        severity_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨",
            "critical": "🔥",
        }
        emoji = severity_emoji.get(severity, "⚠️")

        # Send to Slack
        slack_message_id = await slack.send_notification(
            channel="payments",  # Could be configured
            message=message,
            title=f"{emoji} Payment Issue - Invoice {invoice_data.get('invoice_number')}",
            priority=severity,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message,
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Invoice"},
                            "url": f"/invoices/{invoice_data.get('id')}",
                            "action_id": "view_invoice",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Contact Client"},
                            "action_id": "contact_client",
                            "value": str(invoice_data.get("id")),
                        },
                    ],
                },
            ],
        )

        # Create audit action
        action = InvoiceAction(
            invoice_id=state["invoice_id"],
            workflow_id=state.get("trace_id"),
            action_type="escalated",
            actor="system",
            details={
                "pattern_type": pattern_type,
                "severity": severity,
                "reminder_count": reminder_count,
                "days_overdue": days_overdue,
                "slack_message_id": slack_message_id,
            },
            timestamp=datetime.utcnow(),
        )
        db.add(action)
        await db.commit()

        return {
            "escalated": True,
            "slack_message_id": slack_message_id,
            "steps": state.get("steps", []) + [{
                "node": "escalate_to_slack",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {
                    "escalated": True,
                    "severity": severity,
                    "pattern_type": pattern_type,
                    "slack_message_id": slack_message_id,
                },
                "error": None,
            }],
        }

    except Exception as e:
        return {
            "error": f"Failed to escalate to Slack: {str(e)}",
            "escalated": False,
            "steps": state.get("steps", []) + [{
                "node": "escalate_to_slack",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "error"},
                "error": str(e),
            }],
        }
