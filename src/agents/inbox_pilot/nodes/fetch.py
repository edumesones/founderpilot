"""Fetch email node - retrieves full email data from Gmail."""

from datetime import datetime

from src.agents.inbox_pilot.state import InboxState
from src.integrations.gmail.client import GmailClient


async def fetch_email(
    state: InboxState,
    gmail_client: GmailClient,
) -> dict:
    """Fetch full email data from Gmail.

    This node retrieves the complete email message including:
    - Headers (from, subject, date)
    - Body content (plain text or HTML)
    - Thread context (previous messages)
    - Attachment metadata

    Args:
        state: Current agent state with message_id
        gmail_client: Gmail API client instance

    Returns:
        State update with email data
    """
    message_id = state["message_id"]

    try:
        # Fetch the full message
        email_data = await gmail_client.get_message(
            message_id=message_id,
            include_thread=True,
            thread_limit=5,
        )

        # Record the step
        step = {
            "node": "fetch_email",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "sender": email_data.get("sender"),
                "subject": email_data.get("subject"),
                "body_length": len(email_data.get("body", "")),
                "thread_count": len(email_data.get("thread_messages", [])),
            },
            "error": None,
        }

        return {
            "email": email_data,
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step = {
            "node": "fetch_email",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": str(e),
        }

        return {
            "email": None,
            "error": f"Failed to fetch email: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }
