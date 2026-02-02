"""Slack interactive component handlers."""
import logging
from datetime import datetime
from uuid import UUID

from slack_bolt import Ack, Respond, BoltContext
from slack_sdk import WebClient

from src.integrations.slack.app import get_slack_app
from src.integrations.slack.blocks import (
    build_success_blocks,
    build_error_blocks,
    build_edit_modal,
    build_expired_action_blocks,
    build_meeting_note_modal,
    build_meeting_brief_sent_confirmation,
)
from src.schemas.slack import ActionResult
from src.schemas.meeting_pilot.meeting import MeetingNoteCreate

logger = logging.getLogger(__name__)

# Get the Slack app instance
app = get_slack_app()


# ============================================================================
# Action Handlers
# ============================================================================

@app.action("approve_action")
async def handle_approve(
    ack: Ack,
    body: dict,
    respond: Respond,
    client: WebClient,
    context: BoltContext,
) -> None:
    """
    Handle Approve button click.

    Approves the proposed action and executes it.
    """
    await ack()  # Acknowledge within 3 seconds

    workflow_id = body["actions"][0]["value"]
    user_slack_id = body["user"]["id"]

    logger.info(f"Approve action for workflow {workflow_id} by user {user_slack_id}")

    try:
        # Process the approval
        # Note: In production, this calls the workflow service
        result = await _process_action(
            workflow_id=workflow_id,
            action="approve",
            user_slack_id=user_slack_id,
        )

        if result.success:
            # Update the original message with success
            await respond(
                replace_original=True,
                blocks=build_success_blocks(result),
            )
        else:
            # Show error as ephemeral message
            await respond(
                response_type="ephemeral",
                blocks=build_error_blocks(result.error or "Unknown error"),
            )

    except Exception as e:
        logger.error(f"Error handling approve action: {e}")
        await respond(
            response_type="ephemeral",
            text=f"Error: {str(e)}",
        )


@app.action("reject_action")
async def handle_reject(
    ack: Ack,
    body: dict,
    respond: Respond,
    context: BoltContext,
) -> None:
    """
    Handle Reject button click.

    Rejects the proposed action.
    """
    await ack()

    workflow_id = body["actions"][0]["value"]
    user_slack_id = body["user"]["id"]

    logger.info(f"Reject action for workflow {workflow_id} by user {user_slack_id}")

    try:
        result = await _process_action(
            workflow_id=workflow_id,
            action="reject",
            user_slack_id=user_slack_id,
        )

        if result.success:
            await respond(
                replace_original=True,
                blocks=build_success_blocks(result),
            )
        else:
            await respond(
                response_type="ephemeral",
                blocks=build_error_blocks(result.error or "Unknown error"),
            )

    except Exception as e:
        logger.error(f"Error handling reject action: {e}")
        await respond(
            response_type="ephemeral",
            text=f"Error: {str(e)}",
        )


@app.action("edit_action")
async def handle_edit(
    ack: Ack,
    body: dict,
    client: WebClient,
    context: BoltContext,
) -> None:
    """
    Handle Edit button click.

    Opens a modal for editing the proposed content.
    """
    await ack()

    workflow_id = body["actions"][0]["value"]
    trigger_id = body["trigger_id"]

    logger.info(f"Edit action for workflow {workflow_id}")

    try:
        # Get current content from workflow
        # Note: In production, fetch from workflow service
        current_content = await _get_workflow_content(workflow_id)

        # Open edit modal
        await client.views_open(
            trigger_id=trigger_id,
            view=build_edit_modal(
                workflow_id=UUID(workflow_id),
                current_content=current_content,
            ),
        )

    except Exception as e:
        logger.error(f"Error opening edit modal: {e}")
        # Can't respond in action handler after opening modal
        # Error is logged and user sees generic Slack error


@app.action("snooze_action")
async def handle_snooze(
    ack: Ack,
    body: dict,
    respond: Respond,
    context: BoltContext,
) -> None:
    """
    Handle Snooze button click.

    Snoozes the action for later.
    """
    await ack()

    workflow_id = body["actions"][0]["value"]
    user_slack_id = body["user"]["id"]

    logger.info(f"Snooze action for workflow {workflow_id} by user {user_slack_id}")

    try:
        result = await _process_action(
            workflow_id=workflow_id,
            action="snooze",
            user_slack_id=user_slack_id,
            snooze_minutes=60,  # Default 1 hour
        )

        if result.success:
            await respond(
                replace_original=True,
                blocks=build_success_blocks(result),
            )
        else:
            await respond(
                response_type="ephemeral",
                blocks=build_error_blocks(result.error or "Unknown error"),
            )

    except Exception as e:
        logger.error(f"Error handling snooze action: {e}")
        await respond(
            response_type="ephemeral",
            text=f"Error: {str(e)}",
        )


@app.action("acknowledge_action")
async def handle_acknowledge(
    ack: Ack,
    body: dict,
    respond: Respond,
    context: BoltContext,
) -> None:
    """
    Handle Acknowledge button click (for meeting prep).

    Just marks the item as seen.
    """
    await ack()

    workflow_id = body["actions"][0]["value"]
    user_slack_id = body["user"]["id"]

    logger.info(f"Acknowledge action for workflow {workflow_id}")

    result = ActionResult(
        success=True,
        workflow_id=UUID(workflow_id),
        action="acknowledge",
        summary="Meeting prep acknowledged. Good luck with your meeting!",
        timestamp=datetime.utcnow(),
    )

    await respond(
        replace_original=True,
        blocks=build_success_blocks(result),
    )


# ============================================================================
# MeetingPilot Action Handlers
# ============================================================================

@app.action("meeting_add_note")
async def handle_meeting_add_note(
    ack: Ack,
    body: dict,
    client: WebClient,
    context: BoltContext,
) -> None:
    """
    Handle Add Note button click for meeting brief.

    Opens a modal for adding a pre-meeting note.
    """
    await ack()

    meeting_id = body["actions"][0]["value"]
    trigger_id = body["trigger_id"]

    logger.info(f"Add note action for meeting {meeting_id}")

    try:
        # Get meeting title from the message blocks if available
        meeting_title = _extract_meeting_title(body.get("message", {}))

        # Open note modal
        await client.views_open(
            trigger_id=trigger_id,
            view=build_meeting_note_modal(
                meeting_id=meeting_id,
                meeting_title=meeting_title,
            ),
        )

    except Exception as e:
        logger.error(f"Error opening meeting note modal: {e}")


@app.action("meeting_snooze")
async def handle_meeting_snooze(
    ack: Ack,
    body: dict,
    respond: Respond,
    context: BoltContext,
) -> None:
    """
    Handle Snooze button click for meeting brief.

    Snoozes the brief notification for 10 minutes.
    """
    await ack()

    meeting_id = body["actions"][0]["value"]
    user_slack_id = body["user"]["id"]

    logger.info(f"Snooze meeting brief for meeting {meeting_id} by user {user_slack_id}")

    try:
        result = await _process_meeting_action(
            meeting_id=meeting_id,
            action="snooze",
            user_slack_id=user_slack_id,
            snooze_minutes=10,
        )

        if result.success:
            await respond(
                replace_original=True,
                text=f"⏸️ Brief snoozed for 10 minutes. You'll be reminded before your meeting.",
            )
        else:
            await respond(
                response_type="ephemeral",
                text=f"Error: {result.error or 'Could not snooze brief'}",
            )

    except Exception as e:
        logger.error(f"Error handling meeting snooze: {e}")
        await respond(
            response_type="ephemeral",
            text=f"Error: {str(e)}",
        )


@app.action("meeting_skip")
async def handle_meeting_skip(
    ack: Ack,
    body: dict,
    respond: Respond,
    context: BoltContext,
) -> None:
    """
    Handle Skip button click for meeting brief.

    Skips the brief for this meeting.
    """
    await ack()

    meeting_id = body["actions"][0]["value"]
    user_slack_id = body["user"]["id"]

    logger.info(f"Skip meeting brief for meeting {meeting_id} by user {user_slack_id}")

    try:
        result = await _process_meeting_action(
            meeting_id=meeting_id,
            action="skip",
            user_slack_id=user_slack_id,
        )

        if result.success:
            await respond(
                replace_original=True,
                text="⏭️ Brief skipped for this meeting.",
            )
        else:
            await respond(
                response_type="ephemeral",
                text=f"Error: {result.error or 'Could not skip brief'}",
            )

    except Exception as e:
        logger.error(f"Error handling meeting skip: {e}")
        await respond(
            response_type="ephemeral",
            text=f"Error: {str(e)}",
        )


@app.action("meeting_complete")
async def handle_meeting_complete(
    ack: Ack,
    body: dict,
    respond: Respond,
    context: BoltContext,
) -> None:
    """
    Handle Complete/Done button click for meeting brief.

    Marks the meeting as completed after the brief was read.
    """
    await ack()

    meeting_id = body["actions"][0]["value"]
    user_slack_id = body["user"]["id"]

    logger.info(f"Complete meeting for meeting {meeting_id} by user {user_slack_id}")

    try:
        result = await _process_meeting_action(
            meeting_id=meeting_id,
            action="complete",
            user_slack_id=user_slack_id,
        )

        if result.success:
            # Get meeting title for confirmation
            meeting_title = _extract_meeting_title(body.get("message", {}))
            await respond(
                replace_original=True,
                blocks=build_meeting_brief_sent_confirmation(meeting_title),
            )
        else:
            await respond(
                response_type="ephemeral",
                text=f"Error: {result.error or 'Could not mark meeting as complete'}",
            )

    except Exception as e:
        logger.error(f"Error handling meeting complete: {e}")
        await respond(
            response_type="ephemeral",
            text=f"Error: {str(e)}",
        )


# ============================================================================
# Modal Handlers
# ============================================================================

@app.view("edit_modal_submit")
async def handle_edit_submit(
    ack: Ack,
    body: dict,
    client: WebClient,
    context: BoltContext,
) -> None:
    """
    Handle edit modal submission.

    Updates the content and approves the action.
    """
    await ack()

    # Extract data from modal submission
    values = body["view"]["state"]["values"]
    workflow_id = body["view"]["private_metadata"]
    edited_content = values["edit_block"]["edit_input"]["value"]
    user_slack_id = body["user"]["id"]

    logger.info(f"Edit modal submit for workflow {workflow_id}")

    try:
        result = await _process_action(
            workflow_id=workflow_id,
            action="edit",
            user_slack_id=user_slack_id,
            edited_content=edited_content,
        )

        # Modal closes automatically on ack
        # We need to update the original message
        # This requires the original message's channel and ts
        # For MVP, we'll post a new message to confirm
        # In production, store message_ts in workflow state

        if result.success:
            # Get user's DM channel
            dm_response = await client.conversations_open(users=[user_slack_id])
            channel_id = dm_response["channel"]["id"]

            await client.chat_postMessage(
                channel=channel_id,
                blocks=build_success_blocks(result),
            )

    except Exception as e:
        logger.error(f"Error handling edit submission: {e}")
        # Can't easily show error after modal submit
        # Would need to use response_action: errors


@app.view("meeting_note_modal_submit")
async def handle_meeting_note_submit(
    ack: Ack,
    body: dict,
    client: WebClient,
    context: BoltContext,
) -> None:
    """
    Handle meeting note modal submission.

    Saves the note to the meeting record.
    """
    await ack()

    # Extract data from modal submission
    values = body["view"]["state"]["values"]
    meeting_id = body["view"]["private_metadata"]
    note_content = values["note_content_block"]["note_content_input"]["value"]
    user_slack_id = body["user"]["id"]

    logger.info(f"Meeting note submit for meeting {meeting_id}")

    try:
        # Create note data
        note_data = MeetingNoteCreate(
            content=note_content,
            note_type="pre_meeting",
        )

        result = await _process_meeting_action(
            meeting_id=meeting_id,
            action="add_note",
            user_slack_id=user_slack_id,
            note_content=note_content,
        )

        if result.success:
            # Get user's DM channel
            dm_response = await client.conversations_open(users=[user_slack_id])
            channel_id = dm_response["channel"]["id"]

            await client.chat_postMessage(
                channel=channel_id,
                text="✅ Note added to your meeting prep!",
            )

    except Exception as e:
        logger.error(f"Error handling meeting note submission: {e}")


# ============================================================================
# Event Handlers
# ============================================================================

@app.event("app_uninstalled")
async def handle_app_uninstalled(
    event: dict,
    context: BoltContext,
) -> None:
    """
    Handle app uninstallation.

    Marks the installation as inactive.
    """
    team_id = context.team_id
    logger.info(f"App uninstalled from team {team_id}")

    # The InstallationStore.delete_installation handles this
    # But we may want additional cleanup
    # e.g., pause all agents for this user


@app.event("tokens_revoked")
async def handle_tokens_revoked(
    event: dict,
    context: BoltContext,
) -> None:
    """
    Handle token revocation.

    Similar to uninstall - marks installation as inactive.
    """
    team_id = context.team_id
    logger.info(f"Tokens revoked for team {team_id}")


# ============================================================================
# Helper Functions
# ============================================================================

async def _process_action(
    workflow_id: str,
    action: str,
    user_slack_id: str,
    edited_content: str = None,
    snooze_minutes: int = None,
) -> ActionResult:
    """
    Process a user action on a workflow.

    In production, this calls the WorkflowService.
    For MVP, we return a success result.
    """
    # TODO: Implement actual workflow processing
    # result = await workflow_service.process_action(
    #     workflow_id=UUID(workflow_id),
    #     action=action,
    #     user_slack_id=user_slack_id,
    #     edited_content=edited_content,
    #     snooze_minutes=snooze_minutes,
    # )

    action_summaries = {
        "approve": "Response sent successfully.",
        "reject": "Action rejected and marked as complete.",
        "edit": "Response updated and sent.",
        "snooze": f"Snoozed for {snooze_minutes or 60} minutes. You'll be reminded.",
    }

    return ActionResult(
        success=True,
        workflow_id=UUID(workflow_id),
        action=action,
        summary=action_summaries.get(action, "Action completed."),
        timestamp=datetime.utcnow(),
    )


async def _get_workflow_content(workflow_id: str) -> str:
    """
    Get the current content from a workflow.

    In production, fetches from WorkflowService.
    """
    # TODO: Implement actual workflow content retrieval
    # workflow = await workflow_service.get(workflow_id)
    # return workflow.proposed_response

    return "This is the proposed response content that would be edited."


# ============================================================================
# MeetingPilot Helper Functions
# ============================================================================

async def _process_meeting_action(
    meeting_id: str,
    action: str,
    user_slack_id: str,
    snooze_minutes: int = None,
    note_content: str = None,
) -> ActionResult:
    """
    Process a user action on a meeting brief.

    In production, this calls the MeetingPilotService.
    For MVP, we return a success result.
    """
    # TODO: Implement actual meeting action processing
    # async with get_db() as db:
    #     service = MeetingPilotService(db)
    #     if action == "snooze":
    #         await service.snooze_meeting(meeting_id, snooze_minutes)
    #     elif action == "skip":
    #         await service.complete_meeting(meeting_id, "skipped")
    #     elif action == "complete":
    #         await service.complete_meeting(meeting_id, "completed")
    #     elif action == "add_note":
    #         note_data = MeetingNoteCreate(content=note_content, note_type="pre_meeting")
    #         await service.add_note(meeting_id, user_id, note_data)

    action_summaries = {
        "snooze": f"Brief snoozed for {snooze_minutes or 10} minutes.",
        "skip": "Meeting brief skipped.",
        "complete": "Meeting marked as complete. Good luck!",
        "add_note": "Note added to meeting.",
    }

    return ActionResult(
        success=True,
        workflow_id=UUID(meeting_id) if _is_valid_uuid(meeting_id) else UUID("00000000-0000-0000-0000-000000000000"),
        action=action,
        summary=action_summaries.get(action, "Action completed."),
        timestamp=datetime.utcnow(),
    )


def _extract_meeting_title(message: dict) -> str:
    """
    Extract meeting title from a Slack message's blocks.

    Looks for the header block containing the meeting title.
    """
    blocks = message.get("blocks", [])
    for block in blocks:
        if block.get("type") == "header":
            text = block.get("text", {})
            if text.get("type") == "plain_text":
                title = text.get("text", "")
                # Remove emoji prefix if present
                if title.startswith("📅 "):
                    return title[3:]
                return title
    return "Meeting"


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
