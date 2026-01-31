"""Custom OAuth installation store using PostgreSQL."""
import logging
from typing import Optional
from datetime import datetime

from slack_sdk.oauth.installation_store import InstallationStore
from slack_sdk.oauth.installation_store.models.installation import Installation
from slack_sdk.oauth.installation_store.models.bot import Bot
from cryptography.fernet import Fernet

from src.core.config import settings
from src.core.database import SessionLocal
from src.models.slack_installation import SlackInstallation

logger = logging.getLogger(__name__)


class PostgresInstallationStore(InstallationStore):
    """
    Custom installation store that persists Slack OAuth data to PostgreSQL.

    Tokens are encrypted using Fernet (AES-128) before storage.
    """

    def __init__(self):
        self.cipher = None
        if settings.ENCRYPTION_KEY:
            self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())

    def _encrypt(self, value: str) -> str:
        """Encrypt a string value."""
        if self.cipher is None:
            logger.warning("ENCRYPTION_KEY not set - storing tokens unencrypted")
            return value
        return self.cipher.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        """Decrypt a string value."""
        if self.cipher is None:
            return value
        return self.cipher.decrypt(value.encode()).decode()

    def save(self, installation: Installation) -> None:
        """
        Save an OAuth installation to the database.

        Called by Slack Bolt after successful OAuth flow.
        """
        db = SessionLocal()
        try:
            # Check for existing installation for this team
            existing = db.query(SlackInstallation).filter(
                SlackInstallation.team_id == installation.team_id
            ).first()

            if existing:
                # Update existing installation
                existing.team_name = installation.team_name
                existing.bot_user_id = installation.bot_user_id
                existing.bot_access_token = self._encrypt(installation.bot_token)
                existing.user_slack_id = installation.user_id
                if installation.user_token:
                    existing.user_access_token = self._encrypt(installation.user_token)
                existing.scopes = ",".join(installation.bot_scopes or [])
                existing.updated_at = datetime.utcnow()
                existing.is_active = True

                logger.info(f"Updated Slack installation for team {installation.team_id}")
            else:
                # Create new installation
                # Note: user_id (our internal user) must be set separately via callback
                new_installation = SlackInstallation(
                    team_id=installation.team_id,
                    team_name=installation.team_name,
                    enterprise_id=installation.enterprise_id,
                    bot_user_id=installation.bot_user_id,
                    bot_access_token=self._encrypt(installation.bot_token),
                    user_slack_id=installation.user_id,
                    user_access_token=self._encrypt(installation.user_token) if installation.user_token else None,
                    scopes=",".join(installation.bot_scopes or []),
                    is_active=True,
                )
                db.add(new_installation)

                logger.info(f"Created Slack installation for team {installation.team_id}")

            db.commit()

        except Exception as e:
            logger.error(f"Failed to save Slack installation: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    def find_installation(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        user_id: Optional[str] = None,
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Installation]:
        """
        Find an installation by team ID.

        Called by Slack Bolt to get tokens for API calls.
        """
        if not team_id:
            return None

        db = SessionLocal()
        try:
            query = db.query(SlackInstallation).filter(
                SlackInstallation.team_id == team_id,
                SlackInstallation.is_active == True,
            )

            if enterprise_id:
                query = query.filter(SlackInstallation.enterprise_id == enterprise_id)

            installation = query.first()

            if not installation:
                return None

            # Convert to Slack SDK Installation object
            return Installation(
                app_id=None,  # We don't store app_id
                enterprise_id=installation.enterprise_id,
                team_id=installation.team_id,
                team_name=installation.team_name,
                bot_token=self._decrypt(installation.bot_access_token),
                bot_id=None,
                bot_user_id=installation.bot_user_id,
                bot_scopes=installation.scopes.split(",") if installation.scopes else [],
                user_id=installation.user_slack_id,
                user_token=self._decrypt(installation.user_access_token) if installation.user_access_token else None,
                user_scopes=[],
                installed_at=installation.installed_at,
            )

        except Exception as e:
            logger.error(f"Failed to find Slack installation: {e}")
            return None
        finally:
            db.close()

    def find_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Bot]:
        """
        Find bot info by team ID.

        Called by Slack Bolt to get bot token.
        """
        installation = self.find_installation(
            enterprise_id=enterprise_id,
            team_id=team_id,
            is_enterprise_install=is_enterprise_install,
        )

        if not installation:
            return None

        return Bot(
            app_id=None,
            enterprise_id=installation.enterprise_id,
            team_id=installation.team_id,
            bot_token=installation.bot_token,
            bot_id=None,
            bot_user_id=installation.bot_user_id,
            bot_scopes=installation.bot_scopes,
            installed_at=installation.installed_at,
        )

    def delete_installation(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        user_id: Optional[str] = None,
    ) -> None:
        """
        Delete (deactivate) an installation.

        Called when a user uninstalls the app from their workspace.
        """
        if not team_id:
            return

        db = SessionLocal()
        try:
            installation = db.query(SlackInstallation).filter(
                SlackInstallation.team_id == team_id
            ).first()

            if installation:
                installation.is_active = False
                installation.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Deactivated Slack installation for team {team_id}")

        except Exception as e:
            logger.error(f"Failed to delete Slack installation: {e}")
            db.rollback()
        finally:
            db.close()

    def delete_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
    ) -> None:
        """Delete bot info (same as delete_installation for us)."""
        self.delete_installation(
            enterprise_id=enterprise_id,
            team_id=team_id,
        )
