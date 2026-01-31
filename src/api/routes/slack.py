"""Slack integration API routes."""
import hashlib
import hmac
import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.services.slack_service import SlackService
from src.schemas.slack import (
    SlackStatusResponse,
    SlackOAuthCallbackResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/slack", tags=["slack"])


# ============================================================================
# Dependencies
# ============================================================================

def get_slack_service(db: Session = Depends(get_db)) -> SlackService:
    """Dependency for SlackService."""
    return SlackService(db)


def get_current_user_id() -> UUID:
    """
    Get the current authenticated user ID.

    TODO: Replace with actual JWT auth dependency from FEAT-001.
    """
    # Placeholder - returns a mock user ID
    # In production, this extracts user_id from JWT token
    return UUID("00000000-0000-0000-0000-000000000001")


async def verify_slack_signature(request: Request) -> bool:
    """
    Verify Slack request signature.

    Ensures requests are actually from Slack.
    """
    if not settings.SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not set - skipping verification")
        return True

    signature = request.headers.get("X-Slack-Signature", "")
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")

    # Prevent replay attacks
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    body = await request.body()
    sig_basestring = f"v0:{timestamp}:{body.decode()}"

    my_signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)


# ============================================================================
# OAuth Endpoints
# ============================================================================

@router.get("/install")
async def slack_install(
    user_id: UUID = Depends(get_current_user_id),
) -> RedirectResponse:
    """
    Start Slack OAuth installation flow.

    Redirects user to Slack's OAuth authorize page.
    """
    if not settings.slack_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Slack integration not configured",
        )

    # Build OAuth URL
    # State includes user_id to link installation after callback
    state = f"user:{user_id}"

    scopes = "chat:write,users:read,im:write,im:history"
    redirect_uri = settings.SLACK_REDIRECT_URI or f"{settings.FRONTEND_URL}/api/slack/callback"

    oauth_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={settings.SLACK_CLIENT_ID}"
        f"&scope={scopes}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )

    logger.info(f"Starting Slack OAuth for user {user_id}")
    return RedirectResponse(url=oauth_url)


@router.get("/callback")
async def slack_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    slack_service: SlackService = Depends(get_slack_service),
) -> SlackOAuthCallbackResponse:
    """
    Handle Slack OAuth callback.

    Exchanges code for tokens and stores installation.
    """
    if error:
        logger.warning(f"Slack OAuth error: {error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slack authorization failed: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )

    # Extract user_id from state
    user_id = None
    if state and state.startswith("user:"):
        try:
            user_id = UUID(state.split(":", 1)[1])
        except ValueError:
            pass

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    # Exchange code for tokens
    # Note: Slack Bolt's OAuth handler typically does this,
    # but we're doing it manually for more control
    from slack_sdk.web import WebClient
    from slack_sdk.errors import SlackApiError

    client = WebClient()
    try:
        response = client.oauth_v2_access(
            client_id=settings.SLACK_CLIENT_ID,
            client_secret=settings.SLACK_CLIENT_SECRET,
            code=code,
            redirect_uri=settings.SLACK_REDIRECT_URI,
        )
    except SlackApiError as e:
        logger.error(f"Slack OAuth exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code",
        )

    # The InstallationStore.save() is called by Bolt,
    # but since we're doing manual OAuth, we need to save ourselves
    from src.integrations.slack.oauth import PostgresInstallationStore
    from slack_sdk.oauth.installation_store.models.installation import Installation

    store = PostgresInstallationStore()
    installation = Installation(
        app_id=response.get("app_id"),
        enterprise_id=response.get("enterprise", {}).get("id"),
        team_id=response["team"]["id"],
        team_name=response["team"]["name"],
        bot_token=response["access_token"],
        bot_id=response.get("bot_user_id"),
        bot_user_id=response.get("bot_user_id"),
        bot_scopes=response.get("scope", "").split(","),
        user_id=response.get("authed_user", {}).get("id"),
        user_token=response.get("authed_user", {}).get("access_token"),
        user_scopes=response.get("authed_user", {}).get("scope", "").split(","),
    )
    store.save(installation)

    # Link to our user
    slack_service.link_installation_to_user(
        team_id=response["team"]["id"],
        user_id=user_id,
    )

    # Send welcome message
    import asyncio
    asyncio.create_task(slack_service.send_welcome_message(user_id))

    logger.info(f"Slack connected for user {user_id} to team {response['team']['name']}")

    return SlackOAuthCallbackResponse(
        status="connected",
        team_name=response["team"]["name"],
        bot_user_id=response.get("bot_user_id", ""),
    )


# ============================================================================
# Status Endpoints
# ============================================================================

@router.get("/status", response_model=SlackStatusResponse)
async def slack_status(
    user_id: UUID = Depends(get_current_user_id),
    slack_service: SlackService = Depends(get_slack_service),
) -> SlackStatusResponse:
    """
    Get Slack connection status for current user.
    """
    return slack_service.get_status(user_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def slack_disconnect(
    user_id: UUID = Depends(get_current_user_id),
    slack_service: SlackService = Depends(get_slack_service),
) -> Response:
    """
    Disconnect Slack for current user.
    """
    if not slack_service.disconnect(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Slack connection found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Webhook Endpoints (for Slack events)
# ============================================================================

@router.post("/webhooks/events")
async def slack_events(request: Request) -> dict:
    """
    Handle Slack Events API webhooks.

    Used for URL verification and receiving events.
    """
    # Verify signature
    if not await verify_slack_signature(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    body = await request.json()

    # URL verification challenge
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}

    # Handle events
    event_type = body.get("event", {}).get("type")
    logger.info(f"Received Slack event: {event_type}")

    # Events are handled by Slack Bolt handlers
    # This endpoint just acknowledges receipt
    return {"ok": True}


@router.post("/webhooks/interactive")
async def slack_interactive(request: Request) -> Response:
    """
    Handle Slack interactive components (buttons, modals).

    This endpoint receives button clicks and modal submissions.
    The actual handling is done by Slack Bolt handlers.
    """
    # Verify signature
    if not await verify_slack_signature(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # Interactive payloads come as form-encoded with a "payload" field
    form = await request.form()
    import json
    payload = json.loads(form.get("payload", "{}"))

    logger.info(f"Received Slack interactive: {payload.get('type')}")

    # Acknowledge immediately (required within 3 seconds)
    # Actual processing happens in background via Bolt handlers
    return Response(status_code=status.HTTP_200_OK)
