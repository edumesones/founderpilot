"""Slack Bolt app initialization and configuration."""
import logging
from typing import Optional
from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.core.config import settings
from src.integrations.slack.oauth import PostgresInstallationStore

logger = logging.getLogger(__name__)

# Global app instance
_slack_app: Optional[App] = None


def create_slack_app() -> App:
    """
    Create and configure the Slack Bolt app.

    Uses OAuth settings for multi-tenant installation support.
    Falls back to single bot token for development if OAuth not configured.
    """
    global _slack_app

    if _slack_app is not None:
        return _slack_app

    if not settings.SLACK_SIGNING_SECRET:
        raise ValueError("SLACK_SIGNING_SECRET is required")

    # OAuth mode (production) - supports multiple workspaces
    if settings.slack_configured:
        logger.info("Initializing Slack app with OAuth support")

        oauth_settings = OAuthSettings(
            client_id=settings.SLACK_CLIENT_ID,
            client_secret=settings.SLACK_CLIENT_SECRET,
            scopes=[
                "chat:write",      # Send messages as bot
                "users:read",       # Read user info
                "im:write",         # Open DM channels
                "im:history",       # Read DM history (for context)
            ],
            user_scopes=[],  # No user scopes needed for MVP
            installation_store=PostgresInstallationStore(),
            redirect_uri=settings.SLACK_REDIRECT_URI,
        )

        _slack_app = App(
            signing_secret=settings.SLACK_SIGNING_SECRET,
            oauth_settings=oauth_settings,
        )

    # Development mode - single workspace with bot token
    elif settings.SLACK_BOT_TOKEN:
        logger.info("Initializing Slack app with bot token (dev mode)")

        _slack_app = App(
            token=settings.SLACK_BOT_TOKEN,
            signing_secret=settings.SLACK_SIGNING_SECRET,
        )

    else:
        raise ValueError(
            "Slack not configured. Set SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, "
            "SLACK_SIGNING_SECRET for OAuth, or SLACK_BOT_TOKEN for dev mode."
        )

    # Register handlers
    _register_handlers(_slack_app)

    return _slack_app


def get_slack_app() -> App:
    """Get the initialized Slack app instance."""
    if _slack_app is None:
        return create_slack_app()
    return _slack_app


def start_socket_mode() -> None:
    """
    Start the Slack app in Socket Mode.

    Socket Mode is useful for development as it doesn't require
    a public URL for receiving events.
    """
    if not settings.SLACK_APP_TOKEN:
        raise ValueError("SLACK_APP_TOKEN required for Socket Mode")

    app = get_slack_app()
    handler = SocketModeHandler(app, settings.SLACK_APP_TOKEN)

    logger.info("Starting Slack app in Socket Mode")
    handler.start()


def _register_handlers(app: App) -> None:
    """Register all event and action handlers."""
    # Import handlers to register them with decorators
    from src.integrations.slack import handlers  # noqa: F401

    logger.info("Slack handlers registered")


# ============================================================================
# Middleware
# ============================================================================

def get_slack_client(team_id: str):
    """
    Get a Slack WebClient for a specific team.

    Used when sending messages outside of event handlers.
    """
    from slack_sdk import WebClient
    from src.integrations.slack.oauth import PostgresInstallationStore

    store = PostgresInstallationStore()
    installation = store.find_installation(
        enterprise_id=None,
        team_id=team_id,
    )

    if not installation:
        raise ValueError(f"No installation found for team {team_id}")

    return WebClient(token=installation.bot_token)
