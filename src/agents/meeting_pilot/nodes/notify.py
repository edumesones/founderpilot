"""Notify Slack node - sends meeting brief to user."""

from datetime import datetime
from typing import Any

from src.agents.meeting_pilot.state import MeetingState


async def notify_slack(
    state: MeetingState,
    slack_notifier: Any,  # SlackNotifier
) -> dict:
    """Send meeting brief notification to Slack.

    This node sends the generated brief to the user's Slack DM
    with action buttons for interaction.

    Args:
        state: Current agent state
        slack_notifier: Slack notification client

    Returns:
        State updates with notification status
    """
    step = {
        "node": "notify_slack",
        "timestamp": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }

    try:
        meeting = state.get("meeting")
        brief = state.get("brief")

        if not meeting or not brief:
            raise ValueError("Missing meeting or brief data")

        user_id = state.get("user_id")
        if not user_id:
            raise ValueError("Missing user_id")

        # Build Slack blocks
        blocks = _build_brief_blocks(meeting, brief)

        # Send to user's DM
        message_ts = await slack_notifier.send_dm(
            user_id=user_id,
            blocks=blocks,
            text=f"Upcoming meeting: {meeting['title']}",
        )

        step["result"] = {
            "message_ts": message_ts,
            "meeting_title": meeting["title"],
        }

        return {
            "brief_sent": True,
            "brief_sent_at": datetime.utcnow().isoformat(),
            "slack_message_ts": message_ts,
            "status": "waiting_for_meeting",
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step["error"] = str(e)
        return {
            "error": f"Failed to send Slack notification: {e}",
            "status": "error",
            "steps": state.get("steps", []) + [step],
        }


def _build_brief_blocks(meeting: dict, brief: dict) -> list[dict]:
    """Build Slack Block Kit blocks for meeting brief.

    Args:
        meeting: Meeting data
        brief: Brief result

    Returns:
        List of Slack blocks
    """
    confidence = brief.get("confidence", 0)
    confidence_emoji = (
        ":large_green_circle:" if confidence >= 0.8 else
        ":large_yellow_circle:" if confidence >= 0.5 else
        ":red_circle:"
    )

    # Format attendees
    attendees = meeting.get("attendees", [])
    attendee_list = "\n".join(
        f"• {a.get('name') or a.get('email')}"
        for a in attendees
        if not a.get("is_self")
    )[:500]  # Truncate if too long

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":calendar: Upcoming: {meeting['title'][:100]}",
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*When:*\n{_format_time(meeting['start_time'])}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Duration:*\n{meeting['duration_minutes']} min",
                },
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Participants:*\n{attendee_list}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Context Brief:*\n{brief['content'][:2000]}",
            },
        },
    ]

    # Add warnings if any
    warnings = brief.get("warnings", [])
    if warnings:
        warning_text = "\n".join(f"• {w}" for w in warnings)
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":warning: {warning_text}",
                }
            ],
        })

    # Add confidence and actions
    blocks.extend([
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Confidence: {confidence_emoji} {confidence:.0%}",
                }
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":memo: Add Note"},
                    "action_id": "meeting_add_note",
                    "value": meeting["meeting_id"],
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":alarm_clock: Snooze 10m"},
                    "action_id": "meeting_snooze",
                    "value": meeting["meeting_id"],
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":no_bell: Skip"},
                    "action_id": "meeting_skip",
                    "value": meeting["meeting_id"],
                },
            ],
        },
    ])

    return blocks


def _format_time(iso_time: str) -> str:
    """Format ISO time for display.

    Args:
        iso_time: ISO format datetime string

    Returns:
        Human-readable time string
    """
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return dt.strftime("%a, %b %d at %I:%M %p")
    except Exception:
        return iso_time
