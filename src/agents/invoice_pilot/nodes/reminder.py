"""Reminder flow nodes for InvoicePilot agent."""

from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.invoice_pilot.prompts.reminder import REMINDER_DRAFT_PROMPT
from src.agents.invoice_pilot.state import ReminderState
from src.core.llm import LLMRouter
from src.integrations.gmail.client import GmailClient
from src.integrations.slack.notifier import SlackNotifier
from src.models.invoice import Invoice, InvoiceReminder, InvoiceAction


async def check_reminders_due(
    state: ReminderState,
    db: AsyncSession,
) -> Dict:
    """Check which reminders are due based on invoice due_date and reminder schedule.

    Args:
        state: Current reminder state
        db: Database session

    Returns:
        Updated state with invoice data and reminder metadata
    """
    invoice_id = state["invoice_id"]
    tenant_id = state["tenant_id"]
    config = state.get("config", {})

    try:
        # Fetch invoice with existing reminders
        stmt = select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(["sent", "overdue"]),
        )
        result = await db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice:
            return {
                "error": f"Invoice {invoice_id} not found or not eligible for reminders",
                "steps": state.get("steps", []) + [{
                    "node": "check_reminders_due",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": {"status": "not_found"},
                    "error": f"Invoice {invoice_id} not found",
                }],
            }

        # Calculate days overdue
        today = datetime.utcnow().date()
        due_date = invoice.due_date
        days_overdue = (today - due_date).days if due_date else 0

        # Get reminder schedule from config (default: -3, 3, 7, 14)
        # Negative = before due date, positive = after due date
        reminder_schedule = config.get("reminder_schedule", [-3, 3, 7, 14])

        # Count existing reminders
        stmt = select(InvoiceReminder).where(
            InvoiceReminder.invoice_id == invoice_id,
            InvoiceReminder.status == "sent",
        )
        result = await db.execute(stmt)
        existing_reminders = result.scalars().all()
        reminder_count = len(existing_reminders)

        # Determine if reminder is due
        should_remind = False
        for offset in reminder_schedule:
            if days_overdue == offset and reminder_count < len(reminder_schedule):
                should_remind = True
                break

        return {
            "invoice_data": {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "client_name": invoice.client_name,
                "client_email": invoice.client_email,
                "amount_total": float(invoice.amount_total),
                "amount_paid": float(invoice.amount_paid),
                "currency": invoice.currency,
                "due_date": due_date.isoformat() if due_date else None,
                "status": invoice.status,
            },
            "days_overdue": days_overdue,
            "reminder_count": reminder_count,
            "should_remind": should_remind,
            "steps": state.get("steps", []) + [{
                "node": "check_reminders_due",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {
                    "invoice_id": invoice_id,
                    "days_overdue": days_overdue,
                    "reminder_count": reminder_count,
                    "should_remind": should_remind,
                },
                "error": None,
            }],
        }

    except Exception as e:
        return {
            "error": f"Failed to check reminders: {str(e)}",
            "steps": state.get("steps", []) + [{
                "node": "check_reminders_due",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "error"},
                "error": str(e),
            }],
        }


async def draft_reminder(
    state: ReminderState,
    llm: LLMRouter,
) -> Dict:
    """Generate reminder message using LLM.

    Args:
        state: Current reminder state with invoice data
        llm: LLM router for message generation

    Returns:
        Updated state with draft reminder message
    """
    invoice_data = state.get("invoice_data", {})
    days_overdue = state.get("days_overdue", 0)
    reminder_count = state.get("reminder_count", 0)
    config = state.get("config", {})

    if not invoice_data:
        return {
            "error": "No invoice data available for drafting reminder",
            "steps": state.get("steps", []) + [{
                "node": "draft_reminder",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "no_invoice_data"},
                "error": "No invoice data",
            }],
        }

    try:
        # Determine tone based on reminder count
        tone = "friendly"
        if reminder_count == 0:
            tone = "friendly"
        elif reminder_count == 1:
            tone = "professional"
        elif reminder_count >= 2:
            tone = "firm"

        # Build prompt with invoice context
        prompt = REMINDER_DRAFT_PROMPT.format(
            invoice_number=invoice_data.get("invoice_number", "N/A"),
            client_name=invoice_data.get("client_name", "N/A"),
            amount=f"{invoice_data.get('amount_total', 0):.2f} {invoice_data.get('currency', 'EUR')}",
            due_date=invoice_data.get("due_date", "N/A"),
            days_overdue=days_overdue,
            reminder_count=reminder_count,
            tone=tone,
        )

        # Call LLM
        response = await llm.agenerate(
            prompt=prompt,
            model="gpt-4",
            temperature=0.7,
            max_tokens=500,
        )

        # Parse response (assuming JSON structure from prompt)
        import json
        draft = json.loads(response)

        return {
            "draft": {
                "subject": draft.get("subject", f"Reminder: Invoice {invoice_data.get('invoice_number')}"),
                "body": draft.get("body", ""),
                "tone": tone,
                "confidence": draft.get("confidence", 0.8),
            },
            "steps": state.get("steps", []) + [{
                "node": "draft_reminder",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {
                    "tone": tone,
                    "subject": draft.get("subject", "")[:50],
                },
                "error": None,
            }],
        }

    except Exception as e:
        return {
            "error": f"Failed to draft reminder: {str(e)}",
            "steps": state.get("steps", []) + [{
                "node": "draft_reminder",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "error"},
                "error": str(e),
            }],
        }


async def send_reminder(
    state: ReminderState,
    gmail: GmailClient,
    db: AsyncSession,
) -> Dict:
    """Send reminder email via Gmail API.

    Args:
        state: Current reminder state with draft and approval
        gmail: Gmail client
        db: Database session for storing reminder record

    Returns:
        Updated state with sent status and message ID
    """
    invoice_data = state.get("invoice_data", {})
    draft = state.get("draft") or state.get("edited_draft")
    human_decision = state.get("human_decision")

    if not draft:
        return {
            "error": "No draft available to send",
            "steps": state.get("steps", []) + [{
                "node": "send_reminder",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "no_draft"},
                "error": "No draft",
            }],
        }

    # Check if reminder was skipped
    if human_decision == "skip":
        return {
            "sent": False,
            "sent_message_id": None,
            "skipped": True,
            "steps": state.get("steps", []) + [{
                "node": "send_reminder",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "skipped"},
                "error": None,
            }],
        }

    try:
        # Send email
        message_id = await gmail.send_email(
            to=invoice_data.get("client_email"),
            subject=draft.get("subject"),
            body=draft.get("body"),
            thread_id=None,  # Could thread with original invoice email
        )

        # Create reminder record in DB
        reminder = InvoiceReminder(
            invoice_id=state["invoice_id"],
            scheduled_at=datetime.utcnow(),
            sent_at=datetime.utcnow(),
            type=f"reminder_{state.get('reminder_count', 0) + 1}",
            status="sent",
            draft_message=draft.get("body"),
            final_message=draft.get("body"),
            approved_by=human_decision,
            response_received=False,
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)

        return {
            "reminder_id": reminder.id,
            "sent": True,
            "sent_message_id": message_id,
            "steps": state.get("steps", []) + [{
                "node": "send_reminder",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {
                    "sent": True,
                    "message_id": message_id,
                    "reminder_id": reminder.id,
                },
                "error": None,
            }],
        }

    except Exception as e:
        return {
            "error": f"Failed to send reminder: {str(e)}",
            "sent": False,
            "steps": state.get("steps", []) + [{
                "node": "send_reminder",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "error"},
                "error": str(e),
            }],
        }


async def log_reminder_action(
    state: ReminderState,
    db: AsyncSession,
) -> Dict:
    """Log reminder action to audit trail.

    Args:
        state: Current reminder state
        db: Database session

    Returns:
        Updated state with audit log entry
    """
    invoice_id = state["invoice_id"]
    reminder_id = state.get("reminder_id")
    sent = state.get("sent", False)
    skipped = state.get("skipped", False)

    try:
        # Create audit action
        action = InvoiceAction(
            invoice_id=invoice_id,
            workflow_id=state.get("trace_id"),
            action_type="reminder_sent" if sent else "reminder_skipped",
            actor="system",
            details={
                "reminder_id": reminder_id,
                "sent": sent,
                "skipped": skipped,
                "message_id": state.get("sent_message_id"),
                "decision": state.get("human_decision"),
            },
            timestamp=datetime.utcnow(),
        )
        db.add(action)
        await db.commit()

        return {
            "steps": state.get("steps", []) + [{
                "node": "log_action",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {
                    "action_type": action.action_type,
                    "logged": True,
                },
                "error": None,
            }],
        }

    except Exception as e:
        return {
            "error": f"Failed to log action: {str(e)}",
            "steps": state.get("steps", []) + [{
                "node": "log_action",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {"status": "error"},
                "error": str(e),
            }],
        }
