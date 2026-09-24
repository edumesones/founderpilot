"""Gather context node - fetches email history for participants."""

from datetime import datetime, timedelta
from typing import Any, Optional

from src.agents.meeting_pilot.state import MeetingState, ParticipantContext


async def gather_context(
    state: MeetingState,
    gmail_client: Any,  # GmailClient
    max_emails_per_participant: int = 5,
) -> dict:
    """Gather email context for each meeting participant.

    This node queries Gmail for recent emails with each participant
    to provide context for the meeting brief.

    Args:
        state: Current agent state
        gmail_client: Gmail API client
        max_emails_per_participant: Max emails to fetch per person

    Returns:
        State updates with participant contexts
    """
    step = {
        "node": "gather_context",
        "timestamp": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }

    try:
        meeting = state.get("meeting")
        if not meeting:
            raise ValueError("No meeting data available")

        attendees = meeting.get("attendees", [])
        participant_contexts: list[ParticipantContext] = []

        for attendee in attendees:
            email = attendee.get("email")
            if not email or attendee.get("is_self"):
                continue

            # Query Gmail for emails with this participant
            context = await _get_participant_context(
                gmail_client,
                email,
                attendee.get("name"),
                max_emails_per_participant,
            )
            participant_contexts.append(context)

        step["result"] = {
            "participants_processed": len(participant_contexts),
            "with_history": sum(
                1 for p in participant_contexts if not p["is_first_contact"]
            ),
        }

        return {
            "participant_contexts": participant_contexts,
            "status": "generating_brief",
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step["error"] = str(e)
        return {
            "error": f"Failed to gather context: {e}",
            "status": "error",
            "steps": state.get("steps", []) + [step],
        }


async def _get_participant_context(
    gmail_client: Any,
    email: str,
    name: Optional[str],
    max_emails: int,
) -> ParticipantContext:
    """Get email context for a single participant.

    Args:
        gmail_client: Gmail API client
        email: Participant email address
        name: Participant name (if known)
        max_emails: Max emails to retrieve

    Returns:
        ParticipantContext with email history summary
    """
    try:
        # Search for emails with this participant
        # Query: from:email OR to:email, last 90 days
        query = f"(from:{email} OR to:{email})"

        # Note: This is a simplified implementation.
        # In production, use gmail_client.search_messages() with proper pagination
        messages = await gmail_client.search_messages(
            query=query,
            max_results=max_emails,
        )

        if not messages:
            return ParticipantContext(
                email=email,
                name=name,
                email_count=0,
                recent_subjects=[],
                last_contact=None,
                is_first_contact=True,
                summary=None,
            )

        # Extract subjects and find last contact
        subjects = []
        last_contact = None

        for msg in messages[:max_emails]:
            if msg.get("subject"):
                subjects.append(msg["subject"])
            if msg.get("date") and (not last_contact or msg["date"] > last_contact):
                last_contact = msg["date"]

        return ParticipantContext(
            email=email,
            name=name,
            email_count=len(messages),
            recent_subjects=subjects[:5],
            last_contact=last_contact.isoformat() if last_contact else None,
            is_first_contact=False,
            summary=_generate_context_summary(subjects),
        )

    except Exception:
        # If we can't get context, mark as first contact
        return ParticipantContext(
            email=email,
            name=name,
            email_count=0,
            recent_subjects=[],
            last_contact=None,
            is_first_contact=True,
            summary=None,
        )


def _generate_context_summary(subjects: list[str]) -> Optional[str]:
    """Generate a brief summary of email subjects.

    Args:
        subjects: List of email subjects

    Returns:
        Brief summary string or None
    """
    if not subjects:
        return None

    # Simple summary - in production, use LLM for better summarization
    if len(subjects) == 1:
        return f"Last discussed: {subjects[0]}"

    return f"Recent topics: {', '.join(subjects[:3])}"
