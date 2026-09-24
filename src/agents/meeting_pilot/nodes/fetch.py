"""Fetch meeting node - loads meeting data from database."""

from datetime import datetime
from typing import Any

from src.agents.meeting_pilot.state import MeetingState, MeetingData, AttendeeData


async def fetch_meeting(
    state: MeetingState,
    meeting_record: Any,  # MeetingRecord from DB
) -> dict:
    """Fetch meeting details and prepare for processing.

    This node loads the meeting record from the database and
    converts it to the format needed by subsequent nodes.

    Args:
        state: Current agent state
        meeting_record: MeetingRecord ORM object

    Returns:
        State updates with meeting data
    """
    step = {
        "node": "fetch_meeting",
        "timestamp": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }

    try:
        # Convert attendees to typed format
        attendees: list[AttendeeData] = []
        for att in meeting_record.attendees:
            attendees.append(
                AttendeeData(
                    email=att.get("email", ""),
                    name=att.get("name"),
                    response_status=att.get("response_status", "needsAction"),
                    is_organizer=att.get("is_organizer", False),
                    is_self=att.get("is_self", False),
                )
            )

        # Build meeting data
        meeting: MeetingData = {
            "meeting_id": str(meeting_record.id),
            "calendar_event_id": meeting_record.calendar_event_id,
            "title": meeting_record.title,
            "description": meeting_record.description,
            "start_time": meeting_record.start_time.isoformat(),
            "end_time": meeting_record.end_time.isoformat(),
            "location": meeting_record.location,
            "hangout_link": None,  # Could be in location or description
            "attendees": attendees,
            "is_external": meeting_record.is_external,
            "duration_minutes": meeting_record.duration_minutes,
        }

        step["result"] = {
            "meeting_id": meeting["meeting_id"],
            "title": meeting["title"],
            "attendee_count": len(attendees),
        }

        return {
            "meeting": meeting,
            "status": "gathering_context",
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step["error"] = str(e)
        return {
            "error": f"Failed to fetch meeting: {e}",
            "status": "error",
            "steps": state.get("steps", []) + [step],
        }
