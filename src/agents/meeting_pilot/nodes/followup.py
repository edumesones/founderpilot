"""Suggest follow-up node - generates action items from notes."""

from datetime import datetime
from typing import Any

from src.agents.meeting_pilot.state import MeetingState


async def suggest_followup(
    state: MeetingState,
    llm_router: Any,  # LLMRouter (optional)
) -> dict:
    """Suggest follow-up actions based on meeting notes.

    This node analyzes post-meeting notes and suggests action items
    for the user to follow up on.

    Args:
        state: Current agent state with captured notes
        llm_router: Optional LLM router for AI-generated suggestions

    Returns:
        State updates with follow-up suggestions
    """
    step = {
        "node": "suggest_followup",
        "timestamp": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }

    try:
        notes_content = state.get("notes_content")
        meeting = state.get("meeting")

        suggestions = []

        if notes_content and llm_router:
            # Use LLM to extract action items
            suggestions = await _extract_action_items(
                llm_router,
                notes_content,
                meeting,
            )
        elif notes_content:
            # Simple pattern matching fallback
            suggestions = _extract_action_items_simple(notes_content)

        step["result"] = {
            "suggestion_count": len(suggestions),
            "from_llm": bool(notes_content and llm_router),
        }

        return {
            "follow_up_suggestions": suggestions,
            "status": "completed",
            "action_taken": "completed_with_notes" if notes_content else "completed_no_notes",
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step["error"] = str(e)
        # Don't fail the whole flow for suggestion errors
        return {
            "follow_up_suggestions": [],
            "status": "completed",
            "action_taken": "completed_suggestion_error",
            "steps": state.get("steps", []) + [step],
        }


async def _extract_action_items(
    llm_router: Any,
    notes: str,
    meeting: dict,
) -> list[str]:
    """Use LLM to extract action items from notes.

    Args:
        llm_router: LLM provider router
        notes: Post-meeting notes content
        meeting: Meeting data for context

    Returns:
        List of suggested action items
    """
    prompt = f"""Extract action items from these meeting notes.

Meeting: {meeting.get('title', 'Unknown meeting')}
Participants: {', '.join(a.get('email', '') for a in meeting.get('attendees', [])[:5])}

Notes:
{notes[:2000]}

List up to 5 concrete action items. Each should be a single sentence starting with a verb.
Format: One action per line, starting with "-"
"""

    try:
        response = await llm_router.call(
            task_type="classify",  # Fast model for extraction
            prompt=prompt,
        )

        # Parse response
        items = []
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                item = line[1:].strip()
                if item and len(item) > 5:
                    items.append(item)

        return items[:5]

    except Exception:
        return _extract_action_items_simple(notes)


def _extract_action_items_simple(notes: str) -> list[str]:
    """Simple pattern-based action item extraction.

    Args:
        notes: Post-meeting notes content

    Returns:
        List of potential action items
    """
    items = []
    notes_lower = notes.lower()

    # Look for common action indicators
    action_phrases = [
        "need to",
        "will",
        "should",
        "must",
        "follow up",
        "action:",
        "todo:",
        "next step",
    ]

    for line in notes.split("\n"):
        line = line.strip()
        if not line:
            continue

        line_lower = line.lower()
        for phrase in action_phrases:
            if phrase in line_lower:
                # Clean up the line
                item = line.lstrip("-*•").strip()
                if item and len(item) > 10:
                    items.append(item[:200])
                    break

    return items[:5]
