"""Celery tasks for Slack operations."""
import logging
from typing import Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(SlackApiError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def send_slack_message(
    self,
    channel: str,
    blocks: list,
    token: str,
    text: str = "New notification from FounderPilot",
) -> Optional[str]:
    """
    Send a Slack message asynchronously.

    Args:
        channel: Channel ID to send to
        blocks: Block Kit blocks
        token: Bot token (decrypted)
        text: Fallback text for notifications

    Returns:
        Message timestamp (ts) or None on failure
    """
    client = WebClient(token=token)

    try:
        response = client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=text,
        )
        logger.info(f"Sent Slack message to {channel}")
        return response["ts"]

    except SlackApiError as e:
        error_code = e.response.get("error", "")

        # Handle rate limiting
        if error_code == "ratelimited":
            retry_after = int(e.response.headers.get("Retry-After", 30))
            logger.warning(f"Rate limited, retrying after {retry_after}s")
            raise self.retry(countdown=retry_after)

        # Handle channel not found (don't retry)
        if error_code in ("channel_not_found", "not_in_channel"):
            logger.error(f"Channel {channel} not found or bot not in channel")
            return None

        # Handle invalid token (don't retry)
        if error_code in ("invalid_auth", "token_revoked"):
            logger.error(f"Invalid or revoked token")
            return None

        # Retry other errors
        logger.error(f"Slack API error: {e}")
        raise

    except MaxRetriesExceededError:
        logger.error(f"Max retries exceeded for Slack message to {channel}")
        return None


@shared_task(
    bind=True,
    autoretry_for=(SlackApiError,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def update_slack_message(
    self,
    channel: str,
    ts: str,
    blocks: list,
    token: str,
    text: str = "Updated notification",
) -> bool:
    """
    Update an existing Slack message asynchronously.

    Args:
        channel: Channel ID
        ts: Message timestamp to update
        blocks: New Block Kit blocks
        token: Bot token (decrypted)
        text: Fallback text

    Returns:
        True if updated, False on failure
    """
    client = WebClient(token=token)

    try:
        client.chat_update(
            channel=channel,
            ts=ts,
            blocks=blocks,
            text=text,
        )
        logger.info(f"Updated Slack message {ts} in {channel}")
        return True

    except SlackApiError as e:
        error_code = e.response.get("error", "")

        # Handle rate limiting
        if error_code == "ratelimited":
            retry_after = int(e.response.headers.get("Retry-After", 30))
            raise self.retry(countdown=retry_after)

        # Message not found (don't retry)
        if error_code == "message_not_found":
            logger.warning(f"Message {ts} not found in {channel}")
            return False

        logger.error(f"Failed to update Slack message: {e}")
        raise

    except MaxRetriesExceededError:
        logger.error(f"Max retries exceeded for updating message {ts}")
        return False


@shared_task
def send_welcome_message(user_id: str) -> bool:
    """
    Send welcome message to a new Slack user.

    Args:
        user_id: FounderPilot user ID

    Returns:
        True if sent, False on failure
    """
    from uuid import UUID
    from src.services.slack_service import SlackService

    service = SlackService()

    # Note: This is a sync wrapper around the async method
    # In production, consider using async Celery or a different approach
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        service.send_welcome_message(UUID(user_id))
    )
