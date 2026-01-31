"""
Authentication service handling OAuth flows and session management.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import (
    InvalidTokenError,
    OAuthStateError,
    RefreshTokenError,
)
from src.models.refresh_token import RefreshToken
from src.models.user import User
from src.schemas.auth import GoogleUserInfo, OAuthState
from src.services.audit import AuditService
from src.services.google_oauth import GoogleOAuthService
from src.services.jwt import JWTService


class AuthService:
    """
    Service for handling authentication operations.

    Manages:
    - Google OAuth flow with PKCE
    - User creation/retrieval
    - JWT access tokens
    - Refresh token rotation
    - Session logout and token blacklisting
    """

    # Redis key prefixes
    OAUTH_STATE_PREFIX = "oauth_state:"
    TOKEN_BLACKLIST_PREFIX = "token_blacklist:"

    def __init__(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
        jwt_service: Optional[JWTService] = None,
        google_oauth: Optional[GoogleOAuthService] = None,
        audit_service: Optional[AuditService] = None,
    ):
        """
        Initialize the auth service.

        Args:
            db: Database session
            redis_client: Redis client for state and blacklist storage
            jwt_service: JWT service instance
            google_oauth: Google OAuth service instance
            audit_service: Audit logging service instance
        """
        self.db = db
        self.redis = redis_client
        self.jwt = jwt_service or JWTService()
        self.google = google_oauth or GoogleOAuthService()
        self.audit = audit_service or AuditService(db)

    async def get_google_auth_url(
        self,
        redirect_uri: str,
    ) -> Tuple[str, str, str]:
        """
        Generate Google OAuth authorization URL with PKCE.

        Args:
            redirect_uri: URL to redirect to after authorization

        Returns:
            Tuple of (authorization_url, state, code_verifier)
        """
        state = self.google.generate_state()
        code_verifier = self.google.generate_code_verifier()
        code_challenge = self.google.generate_code_challenge(code_verifier)

        # Store state and verifier in Redis (5 min TTL)
        oauth_state = OAuthState(
            state=state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            created_at=datetime.now(timezone.utc),
        )
        await self._store_oauth_state(state, oauth_state)

        auth_url = self.google.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
        )

        return auth_url, state, code_verifier

    async def handle_google_callback(
        self,
        code: str,
        state: str,
        redirect_uri: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """
        Handle Google OAuth callback.

        Args:
            code: Authorization code from Google
            state: State parameter for CSRF validation
            redirect_uri: Same redirect URI used in authorization request
            ip_address: Client IP for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Tuple of (user, access_token, refresh_token)

        Raises:
            OAuthStateError: If state is invalid or expired
            OAuthCallbackError: If token exchange fails
        """
        # Verify state and get code_verifier
        oauth_state = await self._verify_and_get_oauth_state(state)

        # Exchange code for tokens
        tokens = await self.google.exchange_code(
            code=code,
            redirect_uri=redirect_uri,
            code_verifier=oauth_state.code_verifier,
        )

        # Get user info from Google
        user_info = await self.google.get_user_info(tokens.access_token)

        # Create or get user
        user, is_new = await self._get_or_create_user(user_info)

        # Generate JWT and refresh token
        access_token = self.jwt.create_access_token(user.id)
        refresh_token = await self._create_refresh_token(user.id)

        # Audit log
        if is_new:
            await self.audit.log_signup(
                user_id=user.id,
                provider="google",
                ip_address=ip_address,
                user_agent=user_agent,
            )
        else:
            await self.audit.log_login(
                user_id=user.id,
                provider="google",
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return user, access_token, refresh_token

    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Refresh access and refresh tokens.

        Implements refresh token rotation - the old refresh token is
        invalidated and a new one is issued.

        Args:
            refresh_token: Current refresh token
            ip_address: Client IP for audit logging
            user_agent: Client user agent for audit logging

        Returns:
            Tuple of (new_access_token, new_refresh_token)

        Raises:
            RefreshTokenError: If refresh token is invalid or expired
        """
        # Hash the token to find it
        token_hash = self._hash_token(refresh_token)

        # Find the refresh token in database
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        db_token = result.scalar_one_or_none()

        if not db_token:
            raise RefreshTokenError("Invalid refresh token")

        if not db_token.is_valid:
            raise RefreshTokenError("Refresh token expired or revoked")

        # Revoke old token (rotation)
        db_token.revoked_at = datetime.now(timezone.utc)

        # Create new tokens
        new_access_token = self.jwt.create_access_token(db_token.user_id)
        new_refresh_token = await self._create_refresh_token(db_token.user_id)

        return new_access_token, new_refresh_token

    async def logout(
        self,
        user_id: UUID,
        access_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Logout user and invalidate tokens.

        Args:
            user_id: User ID to logout
            access_token: Current access token to blacklist
            ip_address: Client IP for audit logging
            user_agent: Client user agent for audit logging
        """
        # Revoke all refresh tokens for user
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.revoked_at = datetime.now(timezone.utc)

        # Blacklist current access token if provided
        if access_token:
            await self._blacklist_access_token(access_token)

        # Audit log
        await self.audit.log_logout(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def verify_access_token(self, token: str) -> UUID:
        """
        Verify access token and return user ID.

        Args:
            token: JWT access token

        Returns:
            User ID from token

        Raises:
            InvalidTokenError: If token is invalid or blacklisted
            TokenExpiredError: If token has expired
        """
        # Check blacklist
        if await self._is_token_blacklisted(token):
            raise InvalidTokenError("Token has been revoked")

        # Verify and extract user ID
        return self.jwt.get_user_id_from_token(token)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # Private methods
    # =========================================================================

    async def _store_oauth_state(self, state: str, oauth_state: OAuthState) -> None:
        """Store OAuth state in Redis with 5 min TTL."""
        key = f"{self.OAUTH_STATE_PREFIX}{state}"
        await self.redis.setex(
            key,
            timedelta(minutes=5),
            oauth_state.model_dump_json(),
        )

    async def _verify_and_get_oauth_state(self, state: str) -> OAuthState:
        """Verify state and retrieve OAuth state data from Redis."""
        key = f"{self.OAUTH_STATE_PREFIX}{state}"
        data = await self.redis.get(key)

        if not data:
            raise OAuthStateError("Invalid or expired OAuth state")

        # Delete state after use (one-time use)
        await self.redis.delete(key)

        return OAuthState.model_validate_json(data)

    async def _get_or_create_user(
        self, user_info: GoogleUserInfo
    ) -> Tuple[User, bool]:
        """
        Get existing user or create new one.

        Returns:
            Tuple of (user, is_new)
        """
        # Try to find by google_id
        result = await self.db.execute(
            select(User).where(User.google_id == user_info.id)
        )
        user = result.scalar_one_or_none()

        if user:
            # Update user info if changed
            if user.name != user_info.name or user.picture_url != user_info.picture:
                user.name = user_info.name
                user.picture_url = user_info.picture
            return user, False

        # Create new user
        user = User(
            email=user_info.email,
            name=user_info.name,
            picture_url=user_info.picture,
            google_id=user_info.id,
            onboarding_completed=False,
        )
        self.db.add(user)
        await self.db.flush()

        return user, True

    async def _create_refresh_token(self, user_id: UUID) -> str:
        """Create a new refresh token and store in database."""
        # Generate secure random token
        token = secrets.token_urlsafe(64)
        token_hash = self._hash_token(token)

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

        # Store in database
        db_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(db_token)
        await self.db.flush()

        return token

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def _blacklist_access_token(self, token: str) -> None:
        """Add access token to blacklist in Redis."""
        try:
            # Get token expiration
            exp = self.jwt.get_token_expiration(token)
            ttl = exp - datetime.now(timezone.utc)

            if ttl.total_seconds() > 0:
                key = f"{self.TOKEN_BLACKLIST_PREFIX}{token}"
                await self.redis.setex(key, ttl, "1")
        except Exception:
            # If we can't get expiration, blacklist for max token lifetime
            key = f"{self.TOKEN_BLACKLIST_PREFIX}{token}"
            await self.redis.setex(
                key,
                timedelta(minutes=settings.access_token_expire_minutes),
                "1",
            )

    async def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is in blacklist."""
        key = f"{self.TOKEN_BLACKLIST_PREFIX}{token}"
        return await self.redis.exists(key) > 0
