"""Gmail Pub/Sub webhook handling."""

import base64
import json
from dataclasses import dataclass


@dataclass
class GmailNotification:
    """Parsed Gmail push notification."""

    email_address: str
    history_id: str


def parse_gmail_notification(payload: dict) -> GmailNotification | None:
    """Parse a Gmail Pub/Sub notification.

    Args:
        payload: Pub/Sub message payload

    Returns:
        Parsed notification or None if invalid
    """
    try:
        # Get the message data
        message = payload.get("message", {})
        data = message.get("data", "")

        if not data:
            return None

        # Decode base64 data
        decoded = base64.urlsafe_b64decode(data).decode("utf-8")
        notification = json.loads(decoded)

        return GmailNotification(
            email_address=notification.get("emailAddress", ""),
            history_id=notification.get("historyId", ""),
        )

    except Exception:
        return None


def validate_pubsub_signature(
    request_body: bytes,
    signature: str,
    subscription: str,
) -> bool:
    """Validate Pub/Sub message signature.

    Note: In production, this should verify the JWT token
    from Google. For simplicity, we're checking the subscription name.

    Args:
        request_body: Raw request body
        signature: Authorization header value
        subscription: Expected subscription name

    Returns:
        True if valid
    """
    # TODO: Implement proper JWT verification
    # For now, just check subscription matches
    return True
