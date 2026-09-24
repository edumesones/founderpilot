"""MeetingPilot service - orchestrates meeting preparation workflow."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.calendar.client import CalendarClient
from src.integrations.gmail.client import GmailClient
from src.integrations.slack.notifier import SlackNotifier
from src.core.llm import LLMRouter
from src.models.meeting_pilot.agent_config import MeetingPilotConfig
from src.models.meeting_pilot.meeting_note import MeetingNote
from src.models.meeting_pilot.meeting_record import MeetingRecord
from src.schemas.meeting_pilot.brief import BriefResult
from src.schemas.meeting_pilot.meeting import MeetingNoteCreate, MeetingRecordCreate
from src.integrations.slack.blocks import build_meeting_brief_blocks

logger = logging.getLogger(__name__)


class MeetingPilotService:
    """Service for orchestrating MeetingPilot operations.

    This service handles:
    - Calendar synchronization
    - Meeting processing and brief generation
    - Note management
    - Configuration management
    """

    def __init__(
        self,
        db: AsyncSession,
        calendar_client: Optional[CalendarClient] = None,
        gmail_client: Optional[GmailClient] = None,
        slack_notifier: Optional[SlackNotifier] = None,
        llm_router: Optional[LLMRouter] = None,
    ):
        """Initialize the service.

        Args:
            db: Database session
            calendar_client: Google Calendar client (optional for sync)
            gmail_client: Gmail client for email context
            slack_notifier: Slack notification client
            llm_router: LLM router for brief generation
        """
        self.db = db
        self.calendar = calendar_client
        self.gmail = gmail_client
        self.slack = slack_notifier
        self.llm = llm_router

    # Calendar Sync

    async def sync_calendar(
        self,
        user_id: UUID,
        tenant_id: UUID,
        days_ahead: int = 7,
    ) -> int:
        """Sync calendar events for a user.

        Fetches events from Google Calendar and upserts them to the database.

        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            days_ahead: How many days ahead to sync

        Returns:
            Number of new/updated meetings
        """
        if not self.calendar:
            raise ValueError("Calendar client not configured")

        now = datetime.utcnow()
        time_max = now + timedelta(days=days_ahead)

        # Fetch events from Calendar
        events = await self.calendar.list_events(
            time_min=now,
            time_max=time_max,
        )

        # Get user's email domain for external check
        # In production, get from user record
        user_domain = "example.com"  # TODO: Get from user

        synced_count = 0

        for event in events:
            # Skip cancelled events
            if event.get("status") == "cancelled":
                continue

            # Parse event
            summary = self.calendar.get_event_summary(event)
            start_time, end_time = self.calendar.parse_event_times(event)

            # Check if external
            is_external = self.calendar.is_external_meeting(event, user_domain)

            # Upsert meeting record
            existing = await self._get_meeting_by_event_id(
                user_id, summary["id"]
            )

            if existing:
                # Update existing
                existing.title = summary["title"]
                existing.description = summary["description"]
                existing.start_time = start_time
                existing.end_time = end_time
                existing.location = summary["location"]
                existing.attendees = summary["attendees"]
                existing.is_external = is_external

                if event.get("status") == "cancelled":
                    existing.status = "cancelled"
            else:
                # Create new
                meeting = MeetingRecord(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    calendar_event_id=summary["id"],
                    title=summary["title"],
                    description=summary["description"],
                    start_time=start_time,
                    end_time=end_time,
                    location=summary["location"],
                    attendees=summary["attendees"],
                    is_external=is_external,
                    status="pending",
                )
                self.db.add(meeting)
                synced_count += 1

        await self.db.commit()

        # Update config last_sync_at
        config = await self.get_config(user_id)
        if config:
            config.last_sync_at = datetime.utcnow()
            await self.db.commit()

        logger.info(f"Synced {synced_count} new meetings for user {user_id}")
        return synced_count

    async def _get_meeting_by_event_id(
        self, user_id: UUID, event_id: str
    ) -> Optional[MeetingRecord]:
        """Get meeting by calendar event ID."""
        stmt = select(MeetingRecord).where(
            MeetingRecord.user_id == user_id,
            MeetingRecord.calendar_event_id == event_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # Meeting Processing

    async def get_upcoming_meetings(
        self,
        user_id: UUID,
        minutes_ahead: int = 60,
        only_pending: bool = True,
    ) -> list[MeetingRecord]:
        """Get upcoming meetings that need briefs.

        Args:
            user_id: User UUID
            minutes_ahead: How far ahead to look
            only_pending: Only return meetings with pending status

        Returns:
            List of upcoming meetings
        """
        now = datetime.utcnow()
        time_max = now + timedelta(minutes=minutes_ahead)

        stmt = select(MeetingRecord).where(
            MeetingRecord.user_id == user_id,
            MeetingRecord.start_time >= now,
            MeetingRecord.start_time <= time_max,
        )

        if only_pending:
            stmt = stmt.where(MeetingRecord.status == "pending")

        stmt = stmt.order_by(MeetingRecord.start_time)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_meetings_needing_briefs(
        self,
        user_id: UUID,
    ) -> list[MeetingRecord]:
        """Get meetings that need briefs sent.

        Finds meetings that:
        - Are within the brief window (e.g., 30 min before)
        - Haven't had a brief sent yet
        - Match user's filter criteria

        Args:
            user_id: User UUID

        Returns:
            List of meetings needing briefs
        """
        config = await self.get_config(user_id)
        if not config or not config.is_enabled:
            return []

        brief_minutes = config.brief_minutes_before
        now = datetime.utcnow()

        # Find meetings starting in the next brief_minutes
        # that haven't had briefs sent and aren't snoozed
        stmt = select(MeetingRecord).where(
            MeetingRecord.user_id == user_id,
            MeetingRecord.status == "pending",
            MeetingRecord.brief_sent_at.is_(None),
            MeetingRecord.start_time >= now,
            MeetingRecord.start_time <= now + timedelta(minutes=brief_minutes),
        ).where(
            # Exclude snoozed meetings
            (MeetingRecord.snoozed_until.is_(None)) | (MeetingRecord.snoozed_until <= now)
        )

        if config.only_external_meetings:
            stmt = stmt.where(MeetingRecord.is_external.is_(True))

        stmt = stmt.order_by(MeetingRecord.start_time)

        result = await self.db.execute(stmt)
        meetings = list(result.scalars().all())

        # Filter by min attendees
        return [
            m for m in meetings
            if len(m.attendees) >= config.min_attendees
        ]

    async def get_meeting(self, meeting_id: UUID) -> Optional[MeetingRecord]:
        """Get a meeting by ID."""
        return await self.db.get(MeetingRecord, meeting_id)

    async def mark_brief_sent(
        self,
        meeting_id: UUID,
        brief_content: str,
        confidence: float,
    ) -> None:
        """Mark a meeting as having brief sent.

        Args:
            meeting_id: Meeting UUID
            brief_content: Generated brief content
            confidence: Brief confidence score
        """
        meeting = await self.get_meeting(meeting_id)
        if meeting:
            meeting.brief_sent_at = datetime.utcnow()
            meeting.brief_content = brief_content
            meeting.brief_confidence = confidence
            meeting.status = "brief_sent"
            await self.db.commit()

    async def complete_meeting(
        self, meeting_id: UUID, action: str = "completed"
    ) -> None:
        """Mark a meeting as completed.

        Args:
            meeting_id: Meeting UUID
            action: Action taken (completed, skipped, etc.)
        """
        meeting = await self.get_meeting(meeting_id)
        if meeting:
            meeting.status = action
            await self.db.commit()

    # Notification

    async def send_brief_notification(
        self,
        meeting: MeetingRecord,
        brief: BriefResult,
        user_slack_id: str,
    ) -> bool:
        """Send meeting brief notification via Slack DM.

        Args:
            meeting: Meeting record with all data
            brief: Generated brief result
            user_slack_id: User's Slack ID for DM

        Returns:
            True if notification was sent successfully
        """
        if not self.slack:
            logger.warning("Slack notifier not configured, skipping notification")
            return False

        try:
            # Calculate meeting duration
            duration_minutes = None
            if meeting.start_time and meeting.end_time:
                duration = meeting.end_time - meeting.start_time
                duration_minutes = int(duration.total_seconds() / 60)

            # Build notification blocks
            blocks = build_meeting_brief_blocks(
                meeting_id=str(meeting.id),
                title=meeting.title,
                start_time=meeting.start_time,
                duration_minutes=duration_minutes,
                attendees=meeting.attendees,
                brief_content=brief.content,
                confidence=brief.confidence,
                location=meeting.location,
                warnings=brief.warnings if hasattr(brief, "warnings") else None,
            )

            # Send DM to user
            await self.slack.send_dm(
                user_id=user_slack_id,
                blocks=blocks,
                text=f"📅 Meeting brief: {meeting.title}",
            )

            # Mark brief as sent
            await self.mark_brief_sent(
                meeting_id=meeting.id,
                brief_content=brief.content,
                confidence=brief.confidence,
            )

            # Update stats
            await self.increment_briefs_sent(meeting.user_id)

            logger.info(f"Brief notification sent for meeting {meeting.id}")
            return True

        except Exception as e:
            logger.error(f"Error sending brief notification: {e}")
            return False

    async def snooze_meeting(
        self,
        meeting_id: UUID,
        snooze_minutes: int = 10,
    ) -> None:
        """Snooze a meeting brief notification.

        Delays the brief by the specified minutes.

        Args:
            meeting_id: Meeting UUID
            snooze_minutes: Minutes to delay the brief
        """
        meeting = await self.get_meeting(meeting_id)
        if meeting:
            # Add snooze time to a snooze counter
            # In practice, this delays when the next brief check will pick it up
            meeting.snoozed_until = datetime.utcnow() + timedelta(minutes=snooze_minutes)
            await self.db.commit()
            logger.info(f"Meeting {meeting_id} snoozed for {snooze_minutes} minutes")

    # Notes Management

    async def add_note(
        self,
        meeting_id: UUID,
        user_id: UUID,
        note_data: MeetingNoteCreate,
    ) -> MeetingNote:
        """Add a note to a meeting.

        Args:
            meeting_id: Meeting UUID
            user_id: User UUID
            note_data: Note creation data

        Returns:
            Created MeetingNote
        """
        note = MeetingNote(
            meeting_id=meeting_id,
            user_id=user_id,
            content=note_data.content,
            note_type=note_data.note_type,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def get_meeting_notes(
        self, meeting_id: UUID
    ) -> list[MeetingNote]:
        """Get all notes for a meeting."""
        stmt = select(MeetingNote).where(
            MeetingNote.meeting_id == meeting_id
        ).order_by(MeetingNote.created_at)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # Configuration

    async def get_config(self, user_id: UUID) -> Optional[MeetingPilotConfig]:
        """Get user's MeetingPilot config."""
        stmt = select(MeetingPilotConfig).where(
            MeetingPilotConfig.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update_config(
        self,
        user_id: UUID,
        config_data: dict,
    ) -> MeetingPilotConfig:
        """Create or update user's MeetingPilot config.

        Args:
            user_id: User UUID
            config_data: Configuration data

        Returns:
            Created or updated config
        """
        config = await self.get_config(user_id)

        if config:
            # Update existing
            for key, value in config_data.items():
                if value is not None and hasattr(config, key):
                    setattr(config, key, value)
        else:
            # Create new
            config = MeetingPilotConfig(
                user_id=user_id,
                **config_data,
            )
            self.db.add(config)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    # Statistics

    async def increment_meetings_processed(self, user_id: UUID) -> None:
        """Increment the meetings processed counter."""
        config = await self.get_config(user_id)
        if config:
            config.increment_processed()
            await self.db.commit()

    async def increment_briefs_sent(self, user_id: UUID) -> None:
        """Increment the briefs sent counter."""
        config = await self.get_config(user_id)
        if config:
            config.increment_briefs_sent()
            await self.db.commit()
