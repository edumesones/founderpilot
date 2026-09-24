"""
Integration routes for connecting Gmail and Slack.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from src.api.dependencies import (
    ClientIP,
    CurrentUser,
    DbSession,
    RedisClient,
    UserAgent,
)
from src.core.config import settings
from src.core.exceptions import (
    IntegrationNotFoundError,
    OAuthCallbackError,
    OAuthStateError,
)
from src.schemas.integration import (
    DisconnectResponse,
    IntegrationsStatusResponse,
)
from src.services.gmail_oauth import GmailOAuthService
from src.services.integration import IntegrationService
from src.services.slack_oauth import SlackOAuthService
from src.services.audit import AuditService


router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


# =========================================================================
# Gmail Integration
# =========================================================================


@router.get("/gmail/connect")
async def connect_gmail(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    redis_client: RedisClient,
) -> RedirectResponse:
    """
    Initiate Gmail OAuth2 flow.

    Redirects user to Google's authorization page with Gmail-specific scopes.
    """
    gmail_service = GmailOAuthService(db, redis_client)

    # Build callback URL
    callback_url = str(request.url_for("gmail_callback"))

    # Get authorization URL
    auth_url, state = await gmail_service.get_auth_url(
        user_id=current_user.id,
        redirect_uri=callback_url,
    )

    # Redirect to Google
    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)

    # Set state cookie for additional CSRF protection
    response.set_cookie(
        key="gmail_oauth_state",
        value=state,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=300,
    )

    return response


@router.get("/gmail/callback")
async def gmail_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    db: DbSession = None,
    redis_client: RedisClient = None,
    ip_address: ClientIP = None,
    user_agent: UserAgent = None,
) -> RedirectResponse:
    """
    Handle Gmail OAuth2 callback.

    Exchanges code for tokens and stores the Gmail integration.
    """
    # Check for OAuth errors
    if error:
        error_msg = error_description or error
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.frontend_url}/onboarding/gmail?error={error_msg}",
            status_code=status.HTTP_302_FOUND,
        )

    # Verify state cookie
    cookie_state = request.cookies.get("gmail_oauth_state")
    if not cookie_state or cookie_state != state:
        return RedirectResponse(
            url=f"{settings.frontend_url}/onboarding/gmail?error=invalid_state",
            status_code=status.HTTP_302_FOUND,
        )

    gmail_service = GmailOAuthService(db, redis_client)
    audit_service = AuditService(db)

    try:
        # Handle callback
        callback_url = str(request.url_for("gmail_callback"))
        integration = await gmail_service.handle_callback(
            user_id=current_user.id,
            code=code,
            state=state,
            redirect_uri=callback_url,
        )

        # Audit log
        await audit_service.log_integration_connect(
            user_id=current_user.id,
            provider="gmail",
            scopes=integration.scopes,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    except (OAuthStateError, OAuthCallbackError) as e:
        return RedirectResponse(
            url=f"{settings.frontend_url}/onboarding/gmail?error={e.message}",
            status_code=status.HTTP_302_FOUND,
        )

    # Redirect to next step (Slack)
    response = RedirectResponse(
        url=f"{settings.frontend_url}/onboarding/slack",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie("gmail_oauth_state")
    return response


@router.delete("/gmail", response_model=DisconnectResponse)
async def disconnect_gmail(
    current_user: CurrentUser,
    db: DbSession,
    redis_client: RedisClient,
    ip_address: ClientIP,
    user_agent: UserAgent,
):
    """
    Disconnect Gmail integration.

    Revokes the integration and clears stored tokens.
    """
    integration_service = IntegrationService(db, redis_client)

    try:
        await integration_service.disconnect(
            user_id=current_user.id,
            provider="gmail",
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except IntegrationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gmail integration not found",
        )

    return DisconnectResponse(
        provider="gmail",
        message="Gmail disconnected successfully",
    )


# =========================================================================
# Slack Integration
# =========================================================================


@router.get("/slack/connect")
async def connect_slack(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    redis_client: RedisClient,
) -> RedirectResponse:
    """
    Initiate Slack OAuth2 flow.

    Redirects user to Slack's authorization page to install the bot.
    """
    slack_service = SlackOAuthService(db, redis_client)

    # Build callback URL
    callback_url = str(request.url_for("slack_callback"))

    # Get authorization URL
    auth_url, state = await slack_service.get_auth_url(
        user_id=current_user.id,
        redirect_uri=callback_url,
    )

    # Redirect to Slack
    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)

    # Set state cookie
    response.set_cookie(
        key="slack_oauth_state",
        value=state,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=300,
    )

    return response


@router.get("/slack/callback")
async def slack_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Slack"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    current_user: CurrentUser = None,
    db: DbSession = None,
    redis_client: RedisClient = None,
    ip_address: ClientIP = None,
    user_agent: UserAgent = None,
) -> RedirectResponse:
    """
    Handle Slack OAuth2 callback.

    Installs the bot and stores the Slack integration.
    """
    # Check for OAuth errors
    if error:
        error_msg = error_description or error
        return RedirectResponse(
            url=f"{settings.frontend_url}/onboarding/slack?error={error_msg}",
            status_code=status.HTTP_302_FOUND,
        )

    # Verify state cookie
    cookie_state = request.cookies.get("slack_oauth_state")
    if not cookie_state or cookie_state != state:
        return RedirectResponse(
            url=f"{settings.frontend_url}/onboarding/slack?error=invalid_state",
            status_code=status.HTTP_302_FOUND,
        )

    slack_service = SlackOAuthService(db, redis_client)
    audit_service = AuditService(db)

    try:
        # Handle callback
        integration = await slack_service.handle_callback(
            user_id=current_user.id,
            code=code,
            state=state,
        )

        # Audit log
        await audit_service.log_integration_connect(
            user_id=current_user.id,
            provider="slack",
            scopes=integration.scopes,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    except (OAuthStateError, OAuthCallbackError) as e:
        return RedirectResponse(
            url=f"{settings.frontend_url}/onboarding/slack?error={e.message}",
            status_code=status.HTTP_302_FOUND,
        )

    # Redirect to complete onboarding
    response = RedirectResponse(
        url=f"{settings.frontend_url}/onboarding/complete",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie("slack_oauth_state")
    return response


@router.delete("/slack", response_model=DisconnectResponse)
async def disconnect_slack(
    current_user: CurrentUser,
    db: DbSession,
    redis_client: RedisClient,
    ip_address: ClientIP,
    user_agent: UserAgent,
):
    """
    Disconnect Slack integration.

    Revokes the integration and clears stored tokens.
    """
    integration_service = IntegrationService(db, redis_client)

    try:
        await integration_service.disconnect(
            user_id=current_user.id,
            provider="slack",
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except IntegrationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack integration not found",
        )

    return DisconnectResponse(
        provider="slack",
        message="Slack disconnected successfully",
    )


# =========================================================================
# Integration Status
# =========================================================================


@router.get("/status", response_model=IntegrationsStatusResponse)
async def get_integrations_status(
    current_user: CurrentUser,
    db: DbSession,
    redis_client: RedisClient,
):
    """
    Get status of all integrations.

    Returns connection status for Gmail and Slack.
    """
    integration_service = IntegrationService(db, redis_client)
    return await integration_service.get_status(current_user.id)
