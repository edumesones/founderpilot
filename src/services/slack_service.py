"""High-level Slack operations for FounderPilot agents."""
import logging
from datetime import datetime
from typing import Optional, Union
from uuid import UUID

from cryptography.fernet import Fernet
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import SessionLocal
from src.models.slack_installation import SlackInstallation
from src.schemas.slack import (
    SlackInstallationCreate,
    SlackStatusResponse,
    NotificationPayload,
    EmailNotificationPayload,
    InvoiceNotificationPayload,
    MeetingNotificationPayload,
)
from src.integrations.slack.blocks import (
    build_email_notification,
    build_invoice_notification,
    build_meeting_notification,
    build_welcome_message,
)

logger = logging.getLogger(__name__)


class SlackNotConnectedError(Exception):
    """Raised when trying to send to a user without Slack connected."""

    def __init__(self, user_id: UUID):
        self.user_id = user_id
        super().__init__(f"Slack not connected for user {user_id}")


class SlackService:
    """
    High-level Slack operations for agents to use.

    Handles token encryption, message sending, and installation management.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._cipher = None
        if settings.ENCRYPTION_KEY:
            self._cipher = Fernet(settings.ENCRYPTION_KEY.encode())

    def _get_db(self) -> Session:
        """Get database session, creating one if needed."""
        if self.db is None:
            return SessionLocal()
        return self.db

    def _close_db(self, db: Session) -> None:
        """Close database session if we created it."""
        if self.db is None:
            db.close()

    def _encrypt(self, value: str) -> str:
        """Encrypt a string value."""
        if self._cipher is None:
            logger.warning("ENCRYPTION_KEY not set - storing tokens unencrypted")
            return value
        return self._cipher.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        """Decrypt a string value."""
        if self._cipher is None:
            return value
        return self._cipher.decrypt(value.encode()).decode()

    # ========================================================================
    # Installation Management
    # ========================================================================

    def get_installation(self, user_id: UUID) -> Optional[SlackInstallation]:
        """
        Get user's Slack installation if it exists and is active.

        Args:
            user_id: The FounderPilot user ID

        Returns:
            SlackInstallation or None
        """
        db = self._get_db()
        try:
            return db.query(SlackInstallation).filter(
                SlackInstallation.user_id == user_id,
                SlackInstallation.is_active == True,
            ).first()
        finally:
            self._close_db(db)

    def get_status(self, user_id: UUID) -> SlackStatusResponse:
        """
        Get Slack connection status for a user.

        Args:
            user_id: The FounderPilot user ID

        Returns:
            SlackStatusResponse with connection details
        """
        installation = self.get_installation(user_id)

        if installation and installation.is_connected:
            return SlackStatusResponse(
                connected=True,
                team_name=installation.team_name,
                team_id=installation.team_id,
                installed_at=installation.installed_at,
            )

        return SlackStatusResponse(connected=False)

    def link_installation_to_user(
        self,
        team_id: str,
        user_id: UUID,
    ) -> Optional[SlackInstallation]:
        """
        Link a Slack installation to a FounderPilot user.

        Called after OAuth callback to associate the installation with our user.

        Args:
            team_id: Slack workspace ID
            user_id: FounderPilot user ID

        Returns:
            Updated SlackInstallation or None
        """
        db = self._get_db()
        try:
            installation = db.query(SlackInstallation).filter(
                SlackInstallation.team_id == team_id,
            ).first()

            if installation:
                installation.user_id = user_id
                installation.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(installation)
                return installation

            return None
        except Exception as e:
            logger.error(f"Failed to link installation: {e}")
            db.rollback()
            return None
        finally:
            self._close_db(db)

    def disconnect(self, user_id: UUID) -> bool:
        """
        Disconnect Slack for a user.

        Marks installation as inactive but preserves data.

        Args:
            user_id: The FounderPilot user ID

        Returns:
            True if disconnected, False if no installation found
        """
        db = self._get_db()
        try:
            installation = db.query(SlackInstallation).filter(
                SlackInstallation.user_id == user_id,
            ).first()

            if installation:
                installation.is_active = False
                installation.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Disconnected Slack for user {user_id}")
                return True

            return False
        except Exception as e:
            logger.error(f"Failed to disconnect Slack: {e}")
            db.rollback()
            return False
        finally:
            self._close_db(db)

    # ========================================================================
    # Messaging
    # ========================================================================

    async def send_notification(
        self,
        user_id: UUID,
        payload: Union[
            EmailNotificationPayload,
            InvoiceNotificationPayload,
            MeetingNotificationPayload,
        ],
    ) -> Optional[str]:
        """
        Send a notification to user's Slack DM.

        Args:
            user_id: The FounderPilot user ID
            payload: Notification payload with details

        Returns:
            Message timestamp (ts) for later updates, or None on failure

        Raises:
            SlackNotConnectedError: If user doesn't have Slack connected
        """
        installation = self.get_installation(user_id)
        if not installation or not installation.is_connected:
            raise SlackNotConnectedError(user_id)

        # Build blocks based on notification type
        blocks = self._build_blocks(payload)

        # Get decrypted token
        token = self._decrypt(installation.bot_access_token)
        client = WebClient(token=token)

        try:
            # Ensure we have a DM channel
            channel_id = installation.dm_channel_id
            if not channel_id:
                channel_id = await self._open_dm_channel(
                    client, installation.user_slack_id
                )
                if channel_id:
                    await self._update_dm_channel(installation.id, channel_id)

            if not channel_id:
                logger.error(f"Could not get DM channel for user {user_id}")
                return None

            # Send message
            response = client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=self._get_fallback_text(payload),
            )

            logger.info(
                f"Sent {payload.notification_type} notification to user {user_id}"
            )
            return response["ts"]

        except SlackApiError as e:
            logger.error(f"Slack API error sending notification: {e}")
            return None

    async def update_message(
        self,
        user_id: UUID,
        message_ts: str,
        blocks: list,
    ) -> bool:
        """
        Update an existing Slack message.

        Args:
            user_id: The FounderPilot user ID
            message_ts: Message timestamp to update
            blocks: New Block Kit blocks

        Returns:
            True if updated, False on failure
        """
        installation = self.get_installation(user_id)
        if not installation or not installation.is_connected:
            return False

        token = self._decrypt(installation.bot_access_token)
        client = WebClient(token=token)

        try:
            client.chat_update(
                channel=installation.dm_channel_id,
                ts=message_ts,
                blocks=blocks,
            )
            return True
        except SlackApiError as e:
            logger.error(f"Failed to update Slack message: {e}")
            return False

    async def send_welcome_message(self, user_id: UUID) -> bool:
        """
        Send welcome message after successful Slack connection.

        Args:
            user_id: The FounderPilot user ID

        Returns:
            True if sent, False on failure
        """
        installation = self.get_installation(user_id)
        if not installation:
            return False

        token = self._decrypt(installation.bot_access_token)
        client = WebClient(token=token)

        try:
            # Open DM channel
            dm_response = client.conversations_open(
                users=[installation.user_slack_id]
            )
            channel_id = dm_response["channel"]["id"]

            # Update installation with DM channel
            await self._update_dm_channel(installation.id, channel_id)

            # Send welcome message
            blocks = build_welcome_message(installation.team_name or "Your workspace")
            client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text="Welcome to FounderPilot!",
            )

            logger.info(f"Sent welcome message to user {user_id}")
            return True

        except SlackApiError as e:
            logger.error(f"Failed to send welcome message: {e}")
            return False

    # ========================================================================
    # Private Helpers
    # ========================================================================

    def _build_blocks(
        self,
        payload: Union[
            EmailNotificationPayload,
            InvoiceNotificationPayload,
            MeetingNotificationPayload,
        ],
    ) -> list:
        """Build Block Kit blocks based on notification type."""
        if isinstance(payload, EmailNotificationPayload):
            return build_email_notification(payload)
        elif isinstance(payload, InvoiceNotificationPayload):
            return build_invoice_notification(payload)
        elif isinstance(payload, MeetingNotificationPayload):
            return build_meeting_notification(payload)
        else:
            raise ValueError(f"Unknown notification type: {type(payload)}")

    def _get_fallback_text(
        self,
        payload: Union[
            EmailNotificationPayload,
            InvoiceNotificationPayload,
            MeetingNotificationPayload,
        ],
    ) -> str:
        """Get fallback text for notifications (shown in push notifications)."""
        if isinstance(payload, EmailNotificationPayload):
            return f"Email from {payload.sender}: {payload.subject}"
        elif isinstance(payload, InvoiceNotificationPayload):
            return f"Invoice follow-up: {payload.client_name} - {payload.amount}"
        elif isinstance(payload, MeetingNotificationPayload):
            return f"Meeting prep: {payload.meeting_title}"
        return "New notification from FounderPilot"

    async def _open_dm_channel(
        self,
        client: WebClient,
        user_slack_id: str,
    ) -> Optional[str]:
        """Open a DM channel with a user."""
        try:
            response = client.conversations_open(users=[user_slack_id])
            return response["channel"]["id"]
        except SlackApiError as e:
            logger.error(f"Failed to open DM channel: {e}")
            return None

    async def _update_dm_channel(
        self,
        installation_id: UUID,
        channel_id: str,
    ) -> None:
        """Update the DM channel ID in the installation."""
        db = self._get_db()
        try:
            installation = db.query(SlackInstallation).filter(
                SlackInstallation.id == installation_id,
            ).first()
            if installation:
                installation.dm_channel_id = channel_id
                installation.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Failed to update DM channel: {e}")
            db.rollback()
        finally:
            self._close_db(db)
