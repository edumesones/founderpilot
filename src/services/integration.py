"""
Integration service for managing OAuth integrations.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import IntegrationNotFoundError
from src.models.integration import Integration
from src.schemas.integration import IntegrationStatus, IntegrationsStatusResponse
from src.services.audit import AuditService
from src.services.gmail_oauth import GmailOAuthService
from src.services.slack_oauth import SlackOAuthService


class IntegrationService:
    """
    Service for managing OAuth integrations.

    Provides a unified interface for:
    - Querying integration status
    - Disconnecting integrations
    - Checking if integrations are connected
    """

    # Supported providers
    PROVIDERS = ["gmail", "slack"]

    def __init__(
        self,
        db: AsyncSession,
        redis_client: redis.Redis,
        audit_service: Optional[AuditService] = None,
    ):
        """
        Initialize the integration service.

        Args:
            db: Database session
            redis_client: Redis client
            audit_service: Audit logging service
        """
        self.db = db
        self.redis = redis_client
        self.audit = audit_service or AuditService(db)

        # Initialize provider-specific services
        self.gmail = GmailOAuthService(db, redis_client)
        self.slack = SlackOAuthService(db, redis_client)

    async def get_status(self, user_id: UUID) -> IntegrationsStatusResponse:
        """
        Get status of all integrations for a user.

        Args:
            user_id: The user's ID

        Returns:
            IntegrationsStatusResponse with status of each integration
        """
        # Get all integrations for user
        result = await self.db.execute(
            select(Integration).where(Integration.user_id == user_id)
        )
        integrations = {i.provider: i for i in result.scalars().all()}

        # Build status for Gmail
        gmail_integration = integrations.get("gmail")
        gmail_status = IntegrationStatus(
            provider="gmail",
            connected=gmail_integration is not None and gmail_integration.status == "active",
            connected_at=gmail_integration.connected_at if gmail_integration else None,
            status=gmail_integration.status if gmail_integration else "disconnected",
            scopes=gmail_integration.scopes if gmail_integration else [],
            metadata={},
        )

        # Build status for Slack
        slack_integration = integrations.get("slack")
        slack_status = IntegrationStatus(
            provider="slack",
            connected=slack_integration is not None and slack_integration.status == "active",
            connected_at=slack_integration.connected_at if slack_integration else None,
            status=slack_integration.status if slack_integration else "disconnected",
            scopes=slack_integration.scopes if slack_integration else [],
            metadata=slack_integration.metadata_ if slack_integration else {},
        )

        # Check if all required integrations are connected
        all_connected = gmail_status.connected and slack_status.connected

        return IntegrationsStatusResponse(
            gmail=gmail_status,
            slack=slack_status,
            all_connected=all_connected,
        )

    async def get_integration(
        self,
        user_id: UUID,
        provider: str,
    ) -> Optional[Integration]:
        """
        Get a specific integration for a user.

        Args:
            user_id: The user's ID
            provider: Integration provider (gmail, slack)

        Returns:
            Integration record or None if not found
        """
        result = await self.db.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def is_connected(self, user_id: UUID, provider: str) -> bool:
        """
        Check if a specific integration is connected and active.

        Args:
            user_id: The user's ID
            provider: Integration provider

        Returns:
            True if connected and active
        """
        integration = await self.get_integration(user_id, provider)
        return integration is not None and integration.status == "active"

    async def disconnect(
        self,
        user_id: UUID,
        provider: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Disconnect an integration.

        This marks the integration as revoked but keeps the record for audit purposes.

        Args:
            user_id: The user's ID
            provider: Integration provider to disconnect
            ip_address: Client IP for audit logging
            user_agent: Client user agent for audit logging

        Raises:
            IntegrationNotFoundError: If integration doesn't exist
        """
        integration = await self.get_integration(user_id, provider)

        if not integration:
            raise IntegrationNotFoundError(provider=provider)

        # Mark as revoked
        integration.status = "revoked"
        integration.updated_at = datetime.now(timezone.utc)

        # Clear tokens (security best practice)
        integration.access_token_encrypted = ""
        integration.refresh_token_encrypted = None

        await self.db.flush()

        # Audit log
        await self.audit.log_integration_disconnect(
            user_id=user_id,
            provider=provider,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def verify_connection(self, user_id: UUID, provider: str) -> bool:
        """
        Verify that an integration connection is working.

        Makes an API call to the provider to verify the token is valid.

        Args:
            user_id: The user's ID
            provider: Integration provider

        Returns:
            True if connection is verified working
        """
        if provider == "gmail":
            return await self.gmail.verify_connection(user_id)
        elif provider == "slack":
            return await self.slack.verify_connection(user_id)
        else:
            return False

    async def verify_all_connections(self, user_id: UUID) -> dict[str, bool]:
        """
        Verify all integration connections.

        Args:
            user_id: The user's ID

        Returns:
            Dict of provider -> connection status
        """
        return {
            "gmail": await self.gmail.verify_connection(user_id),
            "slack": await self.slack.verify_connection(user_id),
        }
