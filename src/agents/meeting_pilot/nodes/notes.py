"""Capture notes node - handles post-meeting note capture."""

from datetime import datetime

from src.agents.meeting_pilot.state import MeetingState


async def capture_notes(
    state: MeetingState,
) -> dict:
    """Capture post-meeting notes from user input.

    This node processes notes provided by the user after the meeting
    ends. The actual note content comes from human input via resume().

    Args:
        state: Current agent state with notes_content from human input

    Returns:
        State updates marking notes as captured
    """
    step = {
        "node": "capture_notes",
        "timestamp": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }

    try:
        notes_content = state.get("notes_content")

        if notes_content:
            step["result"] = {
                "notes_length": len(notes_content),
                "has_notes": True,
            }

            return {
                "notes_captured": True,
                "status": "capturing_notes",  # Will move to suggest_followup
                "steps": state.get("steps", []) + [step],
            }
        else:
            # No notes provided - that's OK, move on
            step["result"] = {
                "notes_length": 0,
                "has_notes": False,
            }

            return {
                "notes_captured": False,
                "status": "capturing_notes",
                "steps": state.get("steps", []) + [step],
            }

    except Exception as e:
        step["error"] = str(e)
        return {
            "error": f"Failed to capture notes: {e}",
            "status": "error",
            "steps": state.get("steps", []) + [step],
        }
