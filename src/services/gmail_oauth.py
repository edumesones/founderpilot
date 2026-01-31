"""
Gmail OAuth2 service for connecting Gmail accounts.
"""

import secrets
from datetime import datetime, timezone
from typing import List, Optional
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
    OAuthError,
    OAuthScopeError,
    OAuthStateError,
)
from src.models.integration import Integration
from src.schemas.auth import OAuthState
from src.services.token_encryption import TokenEncryptionService


class GmailOAuthService:
    """
    Service for Gmail OAuth2 authentication.

    Allows users to connect their Gmail accounts for email access.
    Uses the same Google OAuth infrastructure but with Gmail-specific scopes.

    Required scopes:
        - gmail.readonly: Read emails
        - gmail.send: Send emails
        - gmail.labels: Manage labels
    """

    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    # Gmail-specific scopes
    GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.labels",
    ]

    # Redis key prefix for OAuth state
    STATE_PREFIX = "gmail_oauth_state:"

    def __init__(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
        encryption_service: Optional[TokenEncryptionService] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize the Gmail OAuth service.

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
        self.client_id = client_id or settings.gmail_client_id_resolved
        self.client_secret = client_secret or settings.gmail_client_secret_resolved

    @staticmethod
    def generate_state() -> str:
        """Generate a cryptographically secure state parameter."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_code_verifier() -> str:
        """Generate a PKCE code verifier."""
        return secrets.token_urlsafe(64)

    @staticmethod
    def generate_code_challenge(code_verifier: str) -> str:
        """Generate a PKCE code challenge from the verifier."""
        import base64
        import hashlib

        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    async def get_auth_url(
        self,
        user_id: UUID,
        redirect_uri: str,
        additional_scopes: Optional[List[str]] = None,
    ) -> tuple[str, str]:
        """
        Generate Gmail OAuth authorization URL.

        Args:
            user_id: The user ID requesting the connection
            redirect_uri: URL to redirect to after authorization
            additional_scopes: Additional scopes to request

        Returns:
            Tuple of (authorization_url, state)
        """
        state = self.generate_state()
        code_verifier = self.generate_code_verifier()
        code_challenge = self.generate_code_challenge(code_verifier)

        # Combine default and additional scopes
        scopes = list(self.GMAIL_SCOPES)
        if additional_scopes:
            scopes.extend(additional_scopes)

        # Store state with user context
        oauth_state = OAuthState(
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            created_at=datetime.now(timezone.utc),
            user_id=user_id,
        )
        await self._store_oauth_state(state, oauth_state)

        # Build authorization URL
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }

        auth_url = f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
        return auth_url, state

    async def handle_callback(
        self,
        user_id: UUID,
        code: str,
        state: str,
        redirect_uri: str,
    ) -> Integration:
        """
        Handle Gmail OAuth callback.

        Args:
            user_id: The user ID (must match the one used to initiate)
            code: Authorization code from Google
            state: State parameter for validation
            redirect_uri: Same redirect URI used in authorization

        Returns:
            The created/updated Integration record

        Raises:
            OAuthStateError: If state is invalid or user doesn't match
            OAuthCallbackError: If token exchange fails
            OAuthScopeError: If required scopes were not granted
        """
        # Verify state and get stored data
        oauth_state = await self._verify_and_get_oauth_state(state)

        # Verify user matches
        if oauth_state.user_id != user_id:
            raise OAuthStateError("User ID mismatch in OAuth state")

        # Exchange code for tokens
        tokens = await self._exchange_code(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=oauth_state.code_verifier,
        )

        # Verify required scopes
        granted_scopes = tokens.get("scope", "").split()
        self._verify_scopes(granted_scopes)

        # Create or update integration
        integration = await self._create_or_update_integration(
            user_id=user_id,
            tokens=tokens,
            granted_scopes=granted_scopes,
        )

        return integration

    async def refresh_token(self, user_id: UUID) -> Integration:
        """
        Refresh Gmail access token.

        Args:
            user_id: The user's ID

        Returns:
            Updated Integration record

        Raises:
            IntegrationNotFoundError: If no Gmail integration exists
            IntegrationExpiredError: If refresh token is invalid
        """
        # Get existing integration
        result = await self.db.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.provider == "gmail",
            )
        )
        integration = result.scalar_one_or_none()

        if not integration:
            raise IntegrationNotFoundError(provider="gmail")

        if not integration.refresh_token_encrypted:
            raise IntegrationExpiredError(
                message="No refresh token available, reconnection required",
                provider="gmail",
            )

        # Decrypt refresh token
        refresh_token = self.encryption.decrypt(integration.refresh_token_encrypted)

        # Request new access token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                integration.status = "expired"
                raise IntegrationExpiredError(
                    message="Failed to refresh token, reconnection required",
                    provider="gmail",
                )

            tokens = response.json()

        # Update integration with new access token
        integration.access_token_encrypted = self.encryption.encrypt(
            tokens["access_token"]
        )
        integration.token_expires_at = datetime.now(timezone.utc)
        integration.status = "active"
        integration.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        return integration

    async def get_access_token(self, user_id: UUID) -> str:
        """
        Get a valid access token for Gmail API calls.

        Automatically refreshes if expired.

        Args:
            user_id: The user's ID

        Returns:
            Valid access token

        Raises:
            IntegrationNotFoundError: If no Gmail integration exists
            IntegrationExpiredError: If token cannot be refreshed
        """
        result = await self.db.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.provider == "gmail",
            )
        )
        integration = result.scalar_one_or_none()

        if not integration:
            raise IntegrationNotFoundError(provider="gmail")

        if integration.status != "active":
            raise IntegrationExpiredError(
                message="Gmail integration is not active",
                provider="gmail",
            )

        # Check if token needs refresh
        if integration.is_expired:
            integration = await self.refresh_token(user_id)

        return self.encryption.decrypt(integration.access_token_encrypted)

    async def verify_connection(self, user_id: UUID) -> bool:
        """
        Verify that Gmail connection is working.

        Makes a simple API call to verify the access token is valid.

        Args:
            user_id: The user's ID

        Returns:
            True if connection is valid
        """
        try:
            access_token = await self.get_access_token(user_id)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                return response.status_code == 200

        except Exception:
            return False

    # =========================================================================
    # Private methods
    # =========================================================================

    async def _store_oauth_state(self, state: str, oauth_state: OAuthState) -> None:
        """Store OAuth state in Redis with 5 min TTL."""
        from datetime import timedelta

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
        code_verifier: str,
    ) -> dict:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise OAuthCallbackError(
                    message=f"Token exchange failed: {error_data.get('error_description', 'Unknown error')}",
                    provider="gmail",
                )

            return response.json()

    def _verify_scopes(self, granted_scopes: List[str]) -> None:
        """Verify that required scopes were granted."""
        required = set(self.GMAIL_SCOPES)
        granted = set(granted_scopes)

        missing = required - granted
        if missing:
            raise OAuthScopeError(
                message="Required Gmail scopes were not granted",
                provider="gmail",
                required_scopes=list(required),
                granted_scopes=list(granted),
            )

    async def _create_or_update_integration(
        self,
        user_id: UUID,
        tokens: dict,
        granted_scopes: List[str],
    ) -> Integration:
        """Create or update Gmail integration record."""
        # Try to find existing integration
        result = await self.db.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.provider == "gmail",
            )
        )
        integration = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if integration:
            # Update existing
            integration.access_token_encrypted = self.encryption.encrypt(
                tokens["access_token"]
            )
            if tokens.get("refresh_token"):
                integration.refresh_token_encrypted = self.encryption.encrypt(
                    tokens["refresh_token"]
                )
            integration.token_expires_at = now
            integration.scopes = granted_scopes
            integration.status = "active"
            integration.updated_at = now
        else:
            # Create new
            integration = Integration(
                user_id=user_id,
                provider="gmail",
                access_token_encrypted=self.encryption.encrypt(tokens["access_token"]),
                refresh_token_encrypted=(
                    self.encryption.encrypt(tokens["refresh_token"])
                    if tokens.get("refresh_token")
                    else None
                ),
                token_expires_at=now,
                scopes=granted_scopes,
                metadata_={},
                status="active",
                connected_at=now,
            )
            self.db.add(integration)

        await self.db.flush()
        return integration
