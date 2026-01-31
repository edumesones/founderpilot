"""Execute action node - performs the decided action on Gmail."""

from datetime import datetime

from src.agents.inbox_pilot.state import InboxState
from src.integrations.gmail.client import GmailClient


async def execute_action(
    state: InboxState,
    gmail_client: GmailClient,
) -> dict:
    """Execute the decided action on Gmail.

    Possible actions:
    - approve/auto_send: Send the draft response
    - archive: Archive the email
    - reject: Mark as rejected (no Gmail action)
    - ignore: No action taken

    Args:
        state: Current agent state with decision
        gmail_client: Gmail API client

    Returns:
        State update with action_taken
    """
    email = state.get("email")
    draft = state.get("draft")
    human_decision = state.get("human_decision")
    edited_content = state.get("edited_content")
    classification = state.get("classification")

    if not email:
        return {
            "action_taken": "failed",
            "error": "No email data available",
            "steps": state.get("steps", []) + [{
                "node": "execute_action",
                "timestamp": datetime.utcnow().isoformat(),
                "result": None,
                "error": "No email data",
            }],
        }

    message_id = email.get("message_id")

    try:
        # Determine the action to take
        action = _determine_action(state)

        if action in ("approve", "auto_send"):
            # Send the draft (edited version if available)
            content = edited_content or (draft.get("content") if draft else None)

            if content:
                await gmail_client.send_reply(
                    message_id=message_id,
                    body=content,
                )
                action_taken = "sent"
            else:
                action_taken = "failed"

        elif action == "archive":
            await gmail_client.archive(message_id=message_id)
            action_taken = "archived"

        elif action == "reject":
            # Just mark as rejected, no Gmail action
            action_taken = "rejected"

        else:
            # ignore
            action_taken = "ignored"

        # Add label based on classification
        if classification:
            category = classification.get("category", "unknown")
            label_name = f"FP_{category.title()}"
            try:
                await gmail_client.add_label(
                    message_id=message_id,
                    label_name=label_name,
                )
            except Exception:
                # Label failure shouldn't fail the action
                pass

        step = {
            "node": "execute_action",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "action_taken": action_taken,
                "action_requested": action,
            },
            "error": None,
        }

        return {
            "action_taken": action_taken,
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step = {
            "node": "execute_action",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": str(e),
        }

        return {
            "action_taken": "failed",
            "error": f"Action execution failed: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }


def _determine_action(state: InboxState) -> str:
    """Determine what action to take based on state.

    Priority:
    1. Human decision (if available)
    2. Auto-action based on classification and config
    """
    human_decision = state.get("human_decision")

    # If human made a decision, use it
    if human_decision:
        return human_decision

    # Auto-determine based on classification
    classification = state.get("classification")
    draft = state.get("draft")
    config = state.get("config", {})

    if not classification:
        return "ignore"

    category = classification.get("category")
    confidence = classification.get("confidence", 0)

    # Spam -> archive (if auto_archive_spam is enabled)
    if category == "spam" and config.get("auto_archive_spam", True):
        return "archive"

    # High confidence routine with draft -> auto_send (if enabled)
    if (
        category == "routine"
        and draft
        and draft.get("confidence", 0) >= 0.9
        and config.get("auto_send_high_confidence", False)
    ):
        return "auto_send"

    # Default: ignore (human will handle via escalation)
    return "ignore"
