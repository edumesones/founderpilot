"""Celery tasks for MeetingPilot operations."""
import logging
from typing import Optional
from uuid import UUID

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from google.auth.exceptions import GoogleAuthError

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def sync_all_calendars(self) -> dict:
    """
    Sync calendars for all enabled users.

    Runs periodically (every 15 min) to fetch new calendar events.

    Returns:
        Dict with sync statistics
    """
    import asyncio
    from src.core.database import get_async_session
    from src.services.meeting_pilot.service import MeetingPilotService
    from src.integrations.calendar.client import CalendarClient

    async def _sync_all():
        stats = {
            "users_processed": 0,
            "meetings_synced": 0,
            "errors": 0,
        }

        async with get_async_session() as db:
            # Get all users with MeetingPilot enabled
            service = MeetingPilotService(db)

            # TODO: In production, fetch all enabled configs
            # configs = await service.get_all_enabled_configs()
            # For now, this is a placeholder
            configs = []

            for config in configs:
                try:
                    # Create calendar client for user
                    # Note: Need to get user's OAuth tokens
                    calendar_client = await _get_user_calendar_client(config.user_id)
                    if not calendar_client:
                        continue

                    user_service = MeetingPilotService(
                        db=db,
                        calendar_client=calendar_client,
                    )

                    count = await user_service.sync_calendar(
                        user_id=config.user_id,
                        tenant_id=config.tenant_id,
                        days_ahead=7,
                    )

                    stats["users_processed"] += 1
                    stats["meetings_synced"] += count

                except GoogleAuthError:
                    logger.warning(f"Google auth expired for user {config.user_id}")
                    stats["errors"] += 1
                except Exception as e:
                    logger.error(f"Error syncing calendar for user {config.user_id}: {e}")
                    stats["errors"] += 1

        return stats

    # Run async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_sync_all())


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def process_user_meetings(self, user_id: str) -> dict:
    """
    Process upcoming meetings for a single user.

    Checks for meetings needing briefs and triggers brief generation.

    Args:
        user_id: User UUID string

    Returns:
        Dict with processing statistics
    """
    import asyncio
    from src.core.database import get_async_session
    from src.services.meeting_pilot.service import MeetingPilotService
    from src.agents.meeting_pilot.agent import MeetingPilotAgent

    async def _process():
        stats = {
            "meetings_checked": 0,
            "briefs_triggered": 0,
            "errors": 0,
        }

        async with get_async_session() as db:
            service = MeetingPilotService(db)

            # Get meetings that need briefs
            meetings = await service.get_meetings_needing_briefs(UUID(user_id))
            stats["meetings_checked"] = len(meetings)

            for meeting in meetings:
                try:
                    # Trigger brief generation task
                    send_meeting_brief.delay(
                        meeting_id=str(meeting.id),
                        user_id=user_id,
                    )
                    stats["briefs_triggered"] += 1

                except Exception as e:
                    logger.error(f"Error triggering brief for meeting {meeting.id}: {e}")
                    stats["errors"] += 1

        return stats

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_process())


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=2,
)
def send_meeting_brief(
    self,
    meeting_id: str,
    user_id: str,
) -> Optional[dict]:
    """
    Generate and send a meeting brief for a specific meeting.

    Args:
        meeting_id: Meeting UUID string
        user_id: User UUID string

    Returns:
        Dict with brief result or None on failure
    """
    import asyncio
    from src.core.database import get_async_session
    from src.services.meeting_pilot.service import MeetingPilotService
    from src.agents.meeting_pilot.agent import MeetingPilotAgent
    from src.integrations.gmail.client import GmailClient
    from src.integrations.slack.notifier import SlackNotifier
    from src.core.llm import LLMRouter

    async def _send_brief():
        async with get_async_session() as db:
            # Get meeting
            service = MeetingPilotService(db)
            meeting = await service.get_meeting(UUID(meeting_id))

            if not meeting:
                logger.warning(f"Meeting {meeting_id} not found")
                return None

            # Check if brief already sent
            if meeting.brief_sent_at:
                logger.info(f"Brief already sent for meeting {meeting_id}")
                return None

            # Initialize dependencies
            gmail_client = await _get_user_gmail_client(UUID(user_id))
            slack_notifier = await _get_user_slack_notifier(UUID(user_id))
            llm_router = LLMRouter()

            # Create agent
            agent = MeetingPilotAgent(
                db=db,
                gmail_client=gmail_client,
                slack_notifier=slack_notifier,
                llm_router=llm_router,
            )

            # Run agent to generate brief
            result = await agent.run(
                meeting_id=meeting_id,
                user_id=user_id,
            )

            if result.get("brief"):
                # Send notification
                user_slack_id = await _get_user_slack_id(UUID(user_id))
                if user_slack_id:
                    service_with_slack = MeetingPilotService(
                        db=db,
                        slack_notifier=slack_notifier,
                    )
                    await service_with_slack.send_brief_notification(
                        meeting=meeting,
                        brief=result["brief"],
                        user_slack_id=user_slack_id,
                    )

                return {
                    "meeting_id": meeting_id,
                    "brief_generated": True,
                    "confidence": result["brief"].confidence,
                }

            return {
                "meeting_id": meeting_id,
                "brief_generated": False,
                "error": result.get("error"),
            }

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_send_brief())


@shared_task
def check_meetings_needing_briefs() -> dict:
    """
    Periodic task to check for meetings needing briefs.

    Runs every 5 minutes to find meetings approaching their brief window.

    Returns:
        Dict with check statistics
    """
    import asyncio
    from src.core.database import get_async_session
    from src.services.meeting_pilot.service import MeetingPilotService

    async def _check():
        stats = {
            "users_checked": 0,
            "briefs_queued": 0,
        }

        async with get_async_session() as db:
            service = MeetingPilotService(db)

            # TODO: In production, get all enabled users
            # users = await service.get_all_enabled_users()
            users = []

            for user_id in users:
                # Queue processing for each user
                process_user_meetings.delay(str(user_id))
                stats["users_checked"] += 1

        return stats

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_check())


# ============================================================================
# Helper Functions
# ============================================================================

async def _get_user_calendar_client(user_id: UUID):
    """Get calendar client with user's OAuth credentials."""
    # TODO: Implement - fetch user's Google OAuth tokens and create client
    # credentials = await oauth_service.get_google_credentials(user_id)
    # return CalendarClient(credentials=credentials)
    return None


async def _get_user_gmail_client(user_id: UUID):
    """Get Gmail client with user's OAuth credentials."""
    # TODO: Implement - fetch user's Google OAuth tokens
    # credentials = await oauth_service.get_google_credentials(user_id)
    # return GmailClient(credentials=credentials)
    return None


async def _get_user_slack_notifier(user_id: UUID):
    """Get Slack notifier for user's workspace."""
    # TODO: Implement - get user's Slack installation
    # installation = await slack_service.get_installation(user_id)
    # return SlackNotifier(token=installation.bot_token)
    return None


async def _get_user_slack_id(user_id: UUID) -> Optional[str]:
    """Get user's Slack user ID."""
    # TODO: Implement - look up Slack ID from user record
    # user = await user_service.get(user_id)
    # return user.slack_user_id
    return None
