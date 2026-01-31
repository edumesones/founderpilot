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
)
from src.schemas.slack import ActionResult

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
