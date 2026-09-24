"""
Slack OAuth2 service for connecting Slack workspaces.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from uuid import UUID

import httpx
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import (
    IntegrationExpiredError,
    IntegrationNotFoundError,
    OAuthCallbackError,
    OAuthScopeError,
    OAuthStateError,
    ProviderAPIError,
)
from src.models.integration import Integration
from src.schemas.auth import OAuthState
from src.services.token_encryption import TokenEncryptionService


class SlackOAuthService:
    """
    Service for Slack OAuth2 authentication.

    Allows users to connect their Slack workspaces for notifications
    and human-in-the-loop interactions via bot.

    Uses Slack's OAuth 2.0 v2 flow with bot token scopes.

    Required bot scopes:
        - chat:write: Send messages
        - im:write: Send direct messages
        - users:read: Read user info
    """

    AUTHORIZATION_URL = "https://slack.com/oauth/v2/authorize"
    TOKEN_URL = "https://slack.com/api/oauth.v2.access"
    AUTH_TEST_URL = "https://slack.com/api/auth.test"

    # Bot token scopes
    BOT_SCOPES = [
        "chat:write",
        "im:write",
        "users:read",
        "users:read.email",
    ]

    # User token scopes (for user identity)
    USER_SCOPES = [
        "openid",
        "profile",
        "email",
    ]

    # Redis key prefix for OAuth state
    STATE_PREFIX = "slack_oauth_state:"

    def __init__(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
        encryption_service: Optional[TokenEncryptionService] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize the Slack OAuth service.

        Args:
            db: Database session
            redis_client: Redis client for state storage
            encryption_service: Token encryption service
            client_id: OAuth client ID (defaults to settings)
            client_secret: OAuth client secret (defaults to settings)
        """
        self.db = db
        self.redis = redis_client
        self.encryption = encryption_service or TokenEncryptionService()
        self.client_id = client_id or settings.slack_client_id
        self.client_secret = client_secret or settings.slack_client_secret

    @staticmethod
    def generate_state() -> str:
        """Generate a cryptographically secure state parameter."""
        return secrets.token_urlsafe(32)

    async def get_auth_url(
        self,
        user_id: UUID,
        redirect_uri: str,
        additional_bot_scopes: Optional[List[str]] = None,
    ) -> tuple[str, str]:
        """
        Generate Slack OAuth authorization URL.

        Args:
            user_id: The user ID requesting the connection
            redirect_uri: URL to redirect to after authorization
            additional_bot_scopes: Additional bot scopes to request

        Returns:
            Tuple of (authorization_url, state)
        """
        state = self.generate_state()

        # Combine default and additional scopes
        bot_scopes = list(self.BOT_SCOPES)
        if additional_bot_scopes:
            bot_scopes.extend(additional_bot_scopes)

        # Store state with user context
        oauth_state = OAuthState(
            state=state,
            code_verifier="",  # Slack doesn't use PKCE
            redirect_uri=redirect_uri,
            created_at=datetime.now(timezone.utc),
            user_id=user_id,
        )
        await self._store_oauth_state(state, oauth_state)

        # Build authorization URL
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(bot_scopes),
            "user_scope": ",".join(self.USER_SCOPES),
            "state": state,
        }

        auth_url = f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
        return auth_url, state

    async def handle_callback(
        self,
        user_id: UUID,
        code: str,
        state: str,
    ) -> Integration:
        """
        Handle Slack OAuth callback.

        Args:
            user_id: The user ID (must match the one used to initiate)
            code: Authorization code from Slack
            state: State parameter for validation

        Returns:
            The created/updated Integration record

        Raises:
            OAuthStateError: If state is invalid or user doesn't match
            OAuthCallbackError: If token exchange fails
        """
        # Verify state and get stored data
        oauth_state = await self._verify_and_get_oauth_state(state)

        # Verify user matches
        if oauth_state.user_id != user_id:
            raise OAuthStateError("User ID mismatch in OAuth state")

        # Exchange code for tokens
        token_data = await self._exchange_code(
            code=code,
            redirect_uri=oauth_state.redirect_uri,
        )

        # Extract workspace and user info
        workspace_info = await self._extract_workspace_info(token_data)

        # Create or update integration
        integration = await self._create_or_update_integration(
            user_id=user_id,
            token_data=token_data,
            workspace_info=workspace_info,
        )

        return integration

    async def get_bot_token(self, user_id: UUID) -> str:
        """
        Get the bot access token for Slack API calls.

        Args:
            user_id: The user's ID

        Returns:
            Bot access token

        Raises:
            IntegrationNotFoundError: If no Slack integration exists
            IntegrationExpiredError: If integration is not active
        """
        result = await self.db.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.provider == "slack",
            )
        )
        integration = result.scalar_one_or_none()

        if not integration:
            raise IntegrationNotFoundError(provider="slack")

        if integration.status != "active":
            raise IntegrationExpiredError(
                message="Slack integration is not active",
                provider="slack",
            )

        return self.encryption.decrypt(integration.access_token_encrypted)

    async def verify_connection(self, user_id: UUID) -> bool:
        """
        Verify that Slack connection is working.

        Makes auth.test API call to verify the bot token is valid.

        Args:
            user_id: The user's ID

        Returns:
            True if connection is valid
        """
        try:
            bot_token = await self.get_bot_token(user_id)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.AUTH_TEST_URL,
                    headers={"Authorization": f"Bearer {bot_token}"},
                )

                if response.status_code != 200:
                    return False

                data = response.json()
                return data.get("ok", False)

        except Exception:
            return False

    async def get_workspace_info(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get information about the connected Slack workspace.

        Args:
            user_id: The user's ID

        Returns:
            Workspace information dict

        Raises:
            IntegrationNotFoundError: If no Slack integration exists
        """
        result = await self.db.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.provider == "slack",
            )
        )
        integration = result.scalar_one_or_none()

        if not integration:
            raise IntegrationNotFoundError(provider="slack")

        return integration.metadata_

    async def send_message(
        self,
        user_id: UUID,
        channel: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel or DM.

        Args:
            user_id: The user's ID
            channel: Channel ID or user ID for DM
            text: Message text (fallback if blocks provided)
            blocks: Slack Block Kit blocks for rich formatting

        Returns:
            Slack API response

        Raises:
            ProviderAPIError: If message send fails
        """
        bot_token = await self.get_bot_token(user_id)

        payload: Dict[str, Any] = {
            "channel": channel,
            "text": text,
        }
        if blocks:
            payload["blocks"] = blocks

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {bot_token}"},
                json=payload,
            )

            data = response.json()
            if not data.get("ok"):
                raise ProviderAPIError(
                    message=f"Failed to send Slack message: {data.get('error', 'Unknown error')}",
                    provider="slack",
                    details={"error": data.get("error")},
                )

            return data

    # =========================================================================
    # Private methods
    # =========================================================================

    async def _store_oauth_state(self, state: str, oauth_state: OAuthState) -> None:
        """Store OAuth state in Redis with 5 min TTL."""
        key = f"{self.STATE_PREFIX}{state}"
        await self.redis.setex(
            key,
            timedelta(minutes=5),
            oauth_state.model_dump_json(),
        )

    async def _verify_and_get_oauth_state(self, state: str) -> OAuthState:
        """Verify state and retrieve OAuth state data from Redis."""
        key = f"{self.STATE_PREFIX}{state}"
        data = await self.redis.get(key)

        if not data:
            raise OAuthStateError("Invalid or expired OAuth state")

        # Delete state after use
        await self.redis.delete(key)

        return OAuthState.model_validate_json(data)

    async def _exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )

            data = response.json()

            if not data.get("ok"):
                raise OAuthCallbackError(
                    message=f"Slack token exchange failed: {data.get('error', 'Unknown error')}",
                    provider="slack",
                )

            return data

    async def _extract_workspace_info(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract workspace information from token response."""
        return {
            "team_id": token_data.get("team", {}).get("id"),
            "team_name": token_data.get("team", {}).get("name"),
            "bot_user_id": token_data.get("bot_user_id"),
            "authed_user_id": token_data.get("authed_user", {}).get("id"),
            "app_id": token_data.get("app_id"),
        }

    async def _create_or_update_integration(
        self,
        user_id: UUID,
        token_data: Dict[str, Any],
        workspace_info: Dict[str, Any],
    ) -> Integration:
        """Create or update Slack integration record."""
        # Try to find existing integration
        result = await self.db.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.provider == "slack",
            )
        )
        integration = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        bot_token = token_data.get("access_token")
        scopes = token_data.get("scope", "").split(",")

        if integration:
            # Update existing
            integration.access_token_encrypted = self.encryption.encrypt(bot_token)
            integration.scopes = scopes
            integration.metadata_ = workspace_info
            integration.status = "active"
            integration.updated_at = now
        else:
            # Create new
            integration = Integration(
                user_id=user_id,
                provider="slack",
                access_token_encrypted=self.encryption.encrypt(bot_token),
                refresh_token_encrypted=None,  # Slack bot tokens don't expire
                token_expires_at=None,  # No expiry for bot tokens
                scopes=scopes,
                metadata_=workspace_info,
                status="active",
                connected_at=now,
            )
            self.db.add(integration)

        await self.db.flush()
        return integration
