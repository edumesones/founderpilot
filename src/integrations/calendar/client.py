"""Google Calendar API client for MeetingPilot."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Calendar API scopes
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarClient:
    """Google Calendar API client.

    Provides methods to list and fetch calendar events for MeetingPilot.
    Uses the same OAuth flow as Gmail (FEAT-001).
    """

    def __init__(self, credentials: Credentials):
        """Initialize the Calendar client.

        Args:
            credentials: Google OAuth2 credentials with calendar scope
        """
        self.credentials = credentials
        self._service = None

    @property
    def service(self):
        """Lazy-load the Calendar API service."""
        if self._service is None:
            self._service = build("calendar", "v3", credentials=self.credentials)
        return self._service

    async def list_events(
        self,
        time_min: datetime,
        time_max: datetime,
        calendar_id: str = "primary",
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        """List calendar events in a time range.

        Args:
            time_min: Start of time range (inclusive)
            time_max: End of time range (inclusive)
            calendar_id: Calendar to query (default: primary)
            max_results: Maximum number of events to return

        Returns:
            List of event dictionaries from Calendar API

        Raises:
            HttpError: If Calendar API request fails
        """
        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min.isoformat(),
                    timeMax=time_max.isoformat(),
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            logger.info(f"Fetched {len(events)} events from calendar")
            return events

        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            raise

    async def get_event(
        self, event_id: str, calendar_id: str = "primary"
    ) -> Optional[dict[str, Any]]:
        """Get a single event by ID.

        Args:
            event_id: The event ID
            calendar_id: Calendar to query (default: primary)

        Returns:
            Event dictionary or None if not found
        """
        try:
            event = (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )
            return event

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Event {event_id} not found")
                return None
            logger.error(f"Calendar API error: {e}")
            raise

    async def list_upcoming_events(
        self,
        hours_ahead: int = 24,
        calendar_id: str = "primary",
    ) -> list[dict[str, Any]]:
        """List events in the next N hours.

        Convenience method for getting upcoming meetings.

        Args:
            hours_ahead: How many hours ahead to look
            calendar_id: Calendar to query

        Returns:
            List of upcoming events
        """
        now = datetime.utcnow()
        time_max = now + timedelta(hours=hours_ahead)
        return await self.list_events(now, time_max, calendar_id)

    def parse_attendees(
        self, event: dict[str, Any], user_email: str
    ) -> list[dict[str, Any]]:
        """Parse attendees from an event.

        Args:
            event: Calendar event dictionary
            user_email: The authenticated user's email (to identify self)

        Returns:
            List of attendee dicts with: email, name, response_status, is_organizer
        """
        attendees = event.get("attendees", [])
        parsed = []

        for attendee in attendees:
            email = attendee.get("email", "")
            parsed.append(
                {
                    "email": email,
                    "name": attendee.get("displayName", email.split("@")[0]),
                    "response_status": attendee.get("responseStatus", "needsAction"),
                    "is_organizer": attendee.get("organizer", False),
                    "is_self": email.lower() == user_email.lower(),
                }
            )

        return parsed

    def is_external_meeting(
        self, event: dict[str, Any], user_domain: str
    ) -> bool:
        """Check if a meeting has external (non-org) attendees.

        Args:
            event: Calendar event dictionary
            user_domain: The user's email domain (e.g., "company.com")

        Returns:
            True if any attendee is from a different domain
        """
        attendees = event.get("attendees", [])

        for attendee in attendees:
            email = attendee.get("email", "")
            if "@" in email:
                domain = email.split("@")[1].lower()
                if domain != user_domain.lower():
                    return True

        return False

    def parse_event_times(
        self, event: dict[str, Any]
    ) -> tuple[datetime, datetime]:
        """Parse start and end times from an event.

        Handles both dateTime (specific time) and date (all-day) events.

        Args:
            event: Calendar event dictionary

        Returns:
            Tuple of (start_time, end_time) as datetime objects
        """
        start = event.get("start", {})
        end = event.get("end", {})

        # Handle specific time events
        if "dateTime" in start:
            start_time = datetime.fromisoformat(
                start["dateTime"].replace("Z", "+00:00")
            )
            end_time = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
        # Handle all-day events
        else:
            start_date = start.get("date", "")
            end_date = end.get("date", "")
            start_time = datetime.fromisoformat(start_date)
            end_time = datetime.fromisoformat(end_date)

        return start_time, end_time

    def get_event_summary(self, event: dict[str, Any]) -> dict[str, Any]:
        """Extract a summary of relevant event fields.

        Args:
            event: Calendar event dictionary

        Returns:
            Dict with: id, title, description, start_time, end_time, location, attendees
        """
        start_time, end_time = self.parse_event_times(event)

        return {
            "id": event.get("id"),
            "title": event.get("summary", "No title"),
            "description": event.get("description"),
            "start_time": start_time,
            "end_time": end_time,
            "location": event.get("location"),
            "hangout_link": event.get("hangoutLink"),
            "html_link": event.get("htmlLink"),
            "status": event.get("status"),  # confirmed, tentative, cancelled
            "attendees": event.get("attendees", []),
        }
