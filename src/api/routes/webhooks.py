"""Webhook endpoints for external services."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory
from src.integrations.gmail.webhook import parse_gmail_notification
from src.models.user import User
from src.services.inbox_pilot.service import InboxPilotService

router = APIRouter()


@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Handle Gmail Pub/Sub push notifications.

    This endpoint receives notifications when new emails arrive.
    It must respond quickly (< 20s) so we process asynchronously.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Parse the notification
    notification = parse_gmail_notification(payload)

    if not notification:
        # Invalid notification, but return 200 to avoid retries
        return {"status": "ignored", "reason": "Invalid notification format"}

    # Queue the processing in background
    background_tasks.add_task(
        process_gmail_notification,
        email_address=notification.email_address,
        history_id=notification.history_id,
    )

    return {"status": "accepted"}


async def process_gmail_notification(
    email_address: str,
    history_id: str,
):
    """Process Gmail notification in background.

    This fetches the user, gets new messages since last history_id,
    and processes each through the InboxPilot agent.
    """
    async with async_session_factory() as db:
        try:
            # Find user by email
            stmt = select(User).where(User.email == email_address)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return  # User not found, ignore

            if not user.gmail_history_id:
                # No previous history_id, skip (need full sync)
                user.gmail_history_id = history_id
                await db.commit()
                return

            # Create service
            service = InboxPilotService(db=db)

            # Get history changes
            from src.integrations.gmail.client import GmailClient

            gmail_client = GmailClient(
                access_token=user.google_access_token,
                refresh_token=user.google_refresh_token,
                user_email=user.email,
            )

            history = await gmail_client.get_history(
                start_history_id=user.gmail_history_id,
                history_types=["messageAdded"],
            )

            # Process new messages
            for entry in history:
                messages_added = entry.get("messagesAdded", [])
                for msg in messages_added:
                    message_id = msg.get("message", {}).get("id")
                    if message_id:
                        try:
                            await service.process_email(
                                user_id=user.id,
                                message_id=message_id,
                            )
                        except Exception:
                            # Log error but continue processing other messages
                            pass

            # Update history_id
            user.gmail_history_id = history_id
            await db.commit()

        except Exception:
            # Log error
            pass


@router.post("/slack/actions")
async def slack_actions(request: Request):
    """Handle Slack interactive component callbacks.

    This receives action callbacks when users click buttons
    or submit modals in Slack messages.
    """
    # Slack sends form-encoded payload
    form_data = await request.form()
    payload_str = form_data.get("payload")

    if not payload_str:
        raise HTTPException(status_code=400, detail="Missing payload")

    import json
    payload = json.loads(payload_str)

    # Determine the type of interaction
    interaction_type = payload.get("type")

    if interaction_type == "block_actions":
        return await handle_block_actions(payload)
    elif interaction_type == "view_submission":
        return await handle_view_submission(payload)
    else:
        return {"ok": True}


async def handle_block_actions(payload: dict):
    """Handle button clicks in Slack messages."""
    actions = payload.get("actions", [])

    if not actions:
        return {"ok": True}

    action = actions[0]
    action_id = action.get("action_id")
    message_id = action.get("value")

    # Map Slack actions to our actions
    action_map = {
        "inbox_pilot_approve": "approve",
        "inbox_pilot_reject": "reject",
        "inbox_pilot_archive": "archive",
        "inbox_pilot_edit": "edit",
    }

    our_action = action_map.get(action_id)

    if not our_action or not message_id:
        return {"ok": True}

    # Handle edit separately (open modal)
    if our_action == "edit":
        # Get current draft and open modal
        # TODO: Get draft from database
        from src.integrations.slack.notifier import SlackNotifier
        notifier = SlackNotifier()

        trigger_id = payload.get("trigger_id")
        # current_draft = await get_draft_for_message(message_id)

        await notifier.open_edit_modal(
            trigger_id=trigger_id,
            message_id=message_id,
            current_draft="",  # TODO: Get actual draft
        )

        return {"ok": True}

    # Process other actions
    async with async_session_factory() as db:
        service = InboxPilotService(db=db)

        try:
            await service.handle_slack_action(
                message_id=message_id,
                action=our_action,
            )
        except Exception:
            pass

    # Update the Slack message to show action was taken
    # TODO: Update message

    return {"ok": True}


async def handle_view_submission(payload: dict):
    """Handle modal form submissions."""
    callback_id = payload.get("view", {}).get("callback_id")

    if callback_id == "inbox_pilot_edit_modal":
        message_id = payload.get("view", {}).get("private_metadata")
        values = payload.get("view", {}).get("state", {}).get("values", {})

        edited_content = (
            values.get("draft_input", {})
            .get("draft_content", {})
            .get("value", "")
        )

        async with async_session_factory() as db:
            service = InboxPilotService(db=db)

            try:
                await service.handle_slack_action(
                    message_id=message_id,
                    action="edit",
                    edited_content=edited_content,
                )
            except Exception:
                pass

    return {"ok": True}
