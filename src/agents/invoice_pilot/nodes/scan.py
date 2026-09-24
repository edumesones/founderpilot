"""Scan inbox node - fetches sent emails with attachments from Gmail."""

from datetime import datetime

from src.agents.invoice_pilot.state import InvoiceState
from src.integrations.gmail.client import GmailClient


async def scan_inbox(
    state: InvoiceState,
    gmail_client: GmailClient,
) -> dict:
    """Fetch sent email with PDF attachment from Gmail.

    This node retrieves a specific sent email message that was flagged
    for invoice detection. It validates that the email:
    - Was sent by the user (in sent folder)
    - Has at least one attachment
    - Has a PDF attachment

    Args:
        state: Current agent state with gmail_message_id
        gmail_client: Gmail API client instance

    Returns:
        State update with email data
    """
    message_id = state["gmail_message_id"]

    try:
        # Fetch the full message
        email_data = await gmail_client.get_message(
            message_id=message_id,
            include_thread=False,  # Don't need thread for invoices
            thread_limit=0,
        )

        # Validate that this is a sent email
        if "SENT" not in email_data.get("labels", []):
            return {
                "error": "Email is not in SENT folder - cannot be an invoice",
                "steps": state.get("steps", []) + [{
                    "node": "scan_inbox",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": None,
                    "error": "Not a sent email",
                }],
            }

        # Validate attachments exist
        attachments = email_data.get("attachments", [])
        if not attachments:
            return {
                "error": "Email has no attachments - cannot be an invoice",
                "steps": state.get("steps", []) + [{
                    "node": "scan_inbox",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": None,
                    "error": "No attachments",
                }],
            }

        # Check for PDF attachments
        pdf_attachments = [
            att for att in attachments
            if att.get("mimeType") == "application/pdf"
        ]

        if not pdf_attachments:
            return {
                "error": "Email has no PDF attachments - cannot be an invoice",
                "steps": state.get("steps", []) + [{
                    "node": "scan_inbox",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": None,
                    "error": "No PDF attachments",
                }],
            }

        # Record the step
        step = {
            "node": "scan_inbox",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "recipient": email_data.get("recipient", email_data.get("to")),
                "subject": email_data.get("subject"),
                "attachment_count": len(attachments),
                "pdf_count": len(pdf_attachments),
            },
            "error": None,
        }

        # Store email data in state (will be used by detection and extraction)
        return {
            "email_data": email_data,
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step = {
            "node": "scan_inbox",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": str(e),
        }

        return {
            "error": f"Failed to fetch email: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }
