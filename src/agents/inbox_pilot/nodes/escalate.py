"""Escalate node - sends notification to human via Slack."""

from datetime import datetime

from src.agents.inbox_pilot.state import InboxState
from src.integrations.slack.notifier import SlackNotifier


async def escalate_to_human(
    state: InboxState,
    slack_notifier: SlackNotifier,
) -> dict:
    """Send Slack notification for human review.

    This node is called when:
    - Email is classified as urgent
    - Classification confidence is below threshold
    - Draft confidence is below threshold
    - Sender is VIP
    - An error occurred during processing

    Args:
        state: Current agent state
        slack_notifier: Slack notification client

    Returns:
        State update marking needs_human_review=True
    """
    user_id = state.get("user_id")
    email = state.get("email")
    classification = state.get("classification")
    draft = state.get("draft")
    error = state.get("error")

    try:
        # Send Slack notification with email details and actions
        await slack_notifier.send_email_notification(
            user_id=user_id,
            email_data={
                "message_id": state.get("message_id"),
                "sender": email.get("sender") if email else "Unknown",
                "sender_name": email.get("sender_name") if email else None,
                "subject": email.get("subject") if email else "Unknown",
                "snippet": email.get("snippet") if email else None,
                "received_at": email.get("received_at") if email else None,
            },
            classification={
                "category": classification.get("category") if classification else "unknown",
                "confidence": classification.get("confidence") if classification else 0.0,
                "reasoning": classification.get("reasoning") if classification else "N/A",
            },
            draft_content=draft.get("content") if draft else None,
            error_message=error,
        )

        step = {
            "node": "escalate",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "notification_sent": True,
                "reason": _get_escalation_reason(state),
            },
            "error": None,
        }

        return {
            "needs_human_review": True,
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step = {
            "node": "escalate",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": str(e),
        }

        # Even if notification fails, we should still wait for human
        return {
            "needs_human_review": True,
            "error": f"Escalation notification failed: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }


def _get_escalation_reason(state: InboxState) -> str:
    """Determine the reason for escalation."""
    classification = state.get("classification")
    draft = state.get("draft")
    error = state.get("error")
    config = state.get("config", {})

    if error:
        return f"Error during processing: {error}"

    if classification:
        if classification.get("category") == "urgent":
            return "Email classified as urgent"

        if classification.get("confidence", 0) < config.get("escalation_threshold", 0.8):
            return f"Low classification confidence: {classification.get('confidence', 0):.0%}"

    if draft:
        if draft.get("confidence", 0) < config.get("draft_threshold", 0.7):
            return f"Low draft confidence: {draft.get('confidence', 0):.0%}"

    return "Human review required"
