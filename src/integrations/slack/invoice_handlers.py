"""
Slack action handlers for InvoicePilot.

This module provides handlers for Slack interactive actions related to
invoice detection, reminders, and escalations.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.invoice import Invoice, InvoiceReminder, InvoiceAction
from src.services.invoice_service import InvoiceService
from src.services.reminder_service import ReminderService
from src.integrations.gmail.client import GmailClient
from src.integrations.slack.invoice_notifications import (
    build_invoice_paid_notification,
    build_reminder_sent_notification,
)


class InvoiceSlackHandler:
    """Handler for Slack interactions related to invoices."""

    def __init__(
        self,
        db: Session,
        slack_client: Any,
        gmail_client: GmailClient,
        tenant_id: str,
    ):
        """
        Initialize handler.

        Args:
            db: Database session
            slack_client: Slack client instance
            gmail_client: Gmail client instance
            tenant_id: Tenant ID for isolation
        """
        self.db = db
        self.slack_client = slack_client
        self.gmail_client = gmail_client
        self.tenant_id = tenant_id
        self.invoice_service = InvoiceService(db, tenant_id)
        self.reminder_service = ReminderService(db, tenant_id)

    async def handle_confirm_invoice(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle confirm invoice action.

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Response message for Slack
        """
        invoice_id = action.get("value")
        user_email = user.get("email", user.get("name", "Unknown"))

        try:
            # Confirm invoice via service
            invoice = self.invoice_service.confirm_invoice(
                invoice_id=invoice_id,
                confirmed_by=user_email,
            )

            # Log action
            self._log_action(
                invoice_id=invoice_id,
                action_type="invoice_confirmed",
                actor=user_email,
                details={"source": "slack_interaction"},
            )

            return {
                "response_type": "in_channel",
                "replace_original": True,
                "text": (
                    f"✅ Invoice {invoice.invoice_number} confirmed by {user_email}\n"
                    f"Client: {invoice.client_name}\n"
                    f"Amount: {invoice.amount_total} {invoice.currency}"
                ),
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error confirming invoice: {str(e)}",
            }

    async def handle_reject_invoice(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle reject invoice action.

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Response message for Slack
        """
        invoice_id = action.get("value")
        user_email = user.get("email", user.get("name", "Unknown"))

        try:
            # Reject invoice via service
            invoice = self.invoice_service.reject_invoice(
                invoice_id=invoice_id,
                rejected_by=user_email,
            )

            # Log action
            self._log_action(
                invoice_id=invoice_id,
                action_type="invoice_rejected",
                actor=user_email,
                details={"source": "slack_interaction"},
            )

            return {
                "response_type": "in_channel",
                "replace_original": True,
                "text": (
                    f"❌ Invoice {invoice.invoice_number} rejected by {user_email}\n"
                    f"This invoice will not be tracked."
                ),
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error rejecting invoice: {str(e)}",
            }

    async def handle_edit_invoice(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle edit invoice action (opens modal).

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Modal view for editing
        """
        invoice_id = action.get("value")

        try:
            invoice = self.invoice_service.get_invoice(invoice_id)

            # Return modal view for editing
            return {
                "type": "modal",
                "callback_id": f"edit_invoice_modal_{invoice_id}",
                "title": {
                    "type": "plain_text",
                    "text": "Edit Invoice",
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Save & Confirm",
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel",
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "invoice_number",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "invoice_number_input",
                            "initial_value": invoice.invoice_number or "",
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Invoice Number",
                        },
                    },
                    {
                        "type": "input",
                        "block_id": "client_name",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "client_name_input",
                            "initial_value": invoice.client_name or "",
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Client Name",
                        },
                    },
                    {
                        "type": "input",
                        "block_id": "client_email",
                        "element": {
                            "type": "email_text_input",
                            "action_id": "client_email_input",
                            "initial_value": invoice.client_email or "",
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Client Email",
                        },
                    },
                    {
                        "type": "input",
                        "block_id": "amount_total",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "amount_total_input",
                            "initial_value": str(invoice.amount_total),
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Amount",
                        },
                    },
                ],
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error loading invoice: {str(e)}",
            }

    async def handle_approve_reminder(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle approve reminder action.

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Response message for Slack
        """
        reminder_id = action.get("value")
        user_email = user.get("email", user.get("name", "Unknown"))

        try:
            # Approve and send reminder
            reminder = self.reminder_service.approve_reminder(
                reminder_id=reminder_id,
                approved_by=user_email,
            )

            # Send reminder email via Gmail
            invoice = self.invoice_service.get_invoice(reminder.invoice_id)

            message_id = await self.gmail_client.send_email(
                to=invoice.client_email,
                subject=f"Payment Reminder: Invoice {invoice.invoice_number}",
                body=reminder.final_message,
                thread_id=invoice.gmail_message_id,  # Reply to original thread
            )

            # Update reminder as sent
            self.reminder_service.mark_reminder_sent(
                reminder_id=reminder_id,
                message_id=message_id,
            )

            # Log action
            self._log_action(
                invoice_id=invoice.id,
                action_type="reminder_sent",
                actor=user_email,
                details={
                    "reminder_id": reminder_id,
                    "reminder_type": reminder.type,
                    "gmail_message_id": message_id,
                },
            )

            # Send confirmation notification
            notification = build_reminder_sent_notification(
                invoice_data=invoice.__dict__,
                reminder_type=reminder.type,
            )

            return {
                "response_type": "in_channel",
                "replace_original": True,
                **notification,
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error sending reminder: {str(e)}",
            }

    async def handle_edit_reminder(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle edit reminder action (opens modal).

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Modal view for editing
        """
        reminder_id = action.get("value")

        try:
            reminder = self.reminder_service.get_reminder(reminder_id)
            invoice = self.invoice_service.get_invoice(reminder.invoice_id)

            # Return modal view for editing
            return {
                "type": "modal",
                "callback_id": f"edit_reminder_modal_{reminder_id}",
                "title": {
                    "type": "plain_text",
                    "text": "Edit Reminder",
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Approve & Send",
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel",
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*Invoice:* {invoice.invoice_number}\n"
                                f"*Client:* {invoice.client_name}"
                            ),
                        },
                    },
                    {
                        "type": "input",
                        "block_id": "message",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "message_input",
                            "multiline": True,
                            "initial_value": reminder.draft_message,
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Reminder Message",
                        },
                    },
                ],
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error loading reminder: {str(e)}",
            }

    async def handle_skip_reminder(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle skip reminder action.

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Response message for Slack
        """
        reminder_id = action.get("value")
        user_email = user.get("email", user.get("name", "Unknown"))

        try:
            reminder = self.reminder_service.skip_reminder(
                reminder_id=reminder_id,
                skipped_by=user_email,
            )

            invoice = self.invoice_service.get_invoice(reminder.invoice_id)

            # Log action
            self._log_action(
                invoice_id=invoice.id,
                action_type="reminder_skipped",
                actor=user_email,
                details={
                    "reminder_id": reminder_id,
                    "reminder_type": reminder.type,
                },
            )

            return {
                "response_type": "in_channel",
                "replace_original": True,
                "text": (
                    f"⏭️ Reminder skipped by {user_email}\n"
                    f"Invoice: {invoice.invoice_number}\n"
                    f"Client: {invoice.client_name}"
                ),
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error skipping reminder: {str(e)}",
            }

    async def handle_mark_paid_from_escalation(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle mark as paid action from escalation.

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Response message for Slack
        """
        invoice_id = action.get("value")
        user_email = user.get("email", user.get("name", "Unknown"))

        try:
            # Mark invoice as paid
            invoice = self.invoice_service.mark_as_paid(
                invoice_id=invoice_id,
                amount=None,  # Full payment
                marked_by=user_email,
            )

            # Log action
            self._log_action(
                invoice_id=invoice_id,
                action_type="marked_paid",
                actor=user_email,
                details={"source": "escalation_action"},
            )

            # Send notification
            notification = build_invoice_paid_notification(
                invoice_data=invoice.__dict__,
                marked_by=user_email,
            )

            return {
                "response_type": "in_channel",
                "replace_original": True,
                **notification,
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error marking invoice as paid: {str(e)}",
            }

    async def handle_call_client(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle call client action.

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Response message for Slack
        """
        invoice_id = action.get("value")
        user_email = user.get("email", user.get("name", "Unknown"))

        try:
            invoice = self.invoice_service.get_invoice(invoice_id)

            # Log action
            self._log_action(
                invoice_id=invoice_id,
                action_type="call_initiated",
                actor=user_email,
                details={"source": "escalation_action"},
            )

            return {
                "response_type": "ephemeral",
                "text": (
                    f"📞 *Call Client*\n\n"
                    f"*Client:* {invoice.client_name}\n"
                    f"*Email:* {invoice.client_email}\n"
                    f"*Invoice:* {invoice.invoice_number}\n"
                    f"*Amount Due:* {invoice.amount_total - invoice.amount_paid} {invoice.currency}\n\n"
                    f"Action logged. Update status after call."
                ),
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error: {str(e)}",
            }

    async def handle_send_final_notice(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle send final notice action.

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Response message for Slack
        """
        invoice_id = action.get("value")

        try:
            invoice = self.invoice_service.get_invoice(invoice_id)

            # Create urgent reminder
            reminder = self.reminder_service.create_urgent_reminder(
                invoice_id=invoice_id,
                message_type="final_notice",
            )

            return {
                "response_type": "ephemeral",
                "text": (
                    f"📧 Final notice created for invoice {invoice.invoice_number}\n"
                    f"Please review and approve in the reminders queue."
                ),
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error creating final notice: {str(e)}",
            }

    async def handle_add_note_to_invoice(
        self,
        action: Dict[str, Any],
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle add note to invoice action (opens modal).

        Args:
            action: Slack action payload
            user: User who performed action

        Returns:
            Modal view for adding note
        """
        invoice_id = action.get("value")

        try:
            invoice = self.invoice_service.get_invoice(invoice_id)

            return {
                "type": "modal",
                "callback_id": f"add_note_modal_{invoice_id}",
                "title": {
                    "type": "plain_text",
                    "text": "Add Note",
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Save Note",
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel",
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*Invoice:* {invoice.invoice_number}\n"
                                f"*Client:* {invoice.client_name}"
                            ),
                        },
                    },
                    {
                        "type": "input",
                        "block_id": "note",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "note_input",
                            "multiline": True,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Enter your note here...",
                            },
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Note",
                        },
                    },
                ],
            }

        except Exception as e:
            return {
                "response_type": "ephemeral",
                "text": f"❌ Error: {str(e)}",
            }

    def _log_action(
        self,
        invoice_id: str,
        action_type: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an action to the invoice audit trail.

        Args:
            invoice_id: Invoice ID
            action_type: Type of action
            actor: User who performed action
            details: Additional details
        """
        action = InvoiceAction(
            invoice_id=invoice_id,
            action_type=action_type,
            actor=actor,
            details=details or {},
            timestamp=datetime.utcnow(),
        )
        self.db.add(action)
        self.db.commit()


# Action routing map
ACTION_HANDLERS = {
    "confirm_invoice": "handle_confirm_invoice",
    "reject_invoice": "handle_reject_invoice",
    "edit_invoice": "handle_edit_invoice",
    "approve_reminder": "handle_approve_reminder",
    "edit_reminder": "handle_edit_reminder",
    "skip_reminder": "handle_skip_reminder",
    "mark_paid_from_escalation": "handle_mark_paid_from_escalation",
    "call_client": "handle_call_client",
    "send_final_notice": "handle_send_final_notice",
    "add_note_to_invoice": "handle_add_note_to_invoice",
}


async def route_slack_action(
    action_id: str,
    payload: Dict[str, Any],
    handler: InvoiceSlackHandler,
) -> Dict[str, Any]:
    """
    Route Slack action to appropriate handler.

    Args:
        action_id: Action ID from Slack
        payload: Full Slack payload
        handler: Handler instance

    Returns:
        Response for Slack
    """
    handler_method_name = ACTION_HANDLERS.get(action_id)

    if not handler_method_name:
        return {
            "response_type": "ephemeral",
            "text": f"❌ Unknown action: {action_id}",
        }

    handler_method = getattr(handler, handler_method_name)
    action = payload.get("actions", [{}])[0]
    user = payload.get("user", {})

    return await handler_method(action, user)
