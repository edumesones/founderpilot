"""
Audit logging service for tracking security-relevant actions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditAction, AuditLog


class AuditService:
    """
    Service for creating and querying audit logs.

    All security-relevant actions should be logged through this service
    to maintain a complete audit trail.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the audit service.

        Args:
            db: Database session
        """
        self.db = db

    async def log(
        self,
        action: str,
        user_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create a new audit log entry.

        Args:
            action: The action performed (use AuditAction constants)
            user_id: The user who performed the action (optional for pre-auth)
            details: Additional action-specific details
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            The created AuditLog entry
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(audit_log)
        await self.db.flush()

        return audit_log

    async def log_signup(
        self,
        user_id: UUID,
        provider: str = "google",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log a user signup event."""
        return await self.log(
            action=AuditAction.SIGNUP,
            user_id=user_id,
            details={"provider": provider},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_login(
        self,
        user_id: UUID,
        provider: str = "google",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log a user login event."""
        return await self.log(
            action=AuditAction.LOGIN,
            user_id=user_id,
            details={"provider": provider},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_logout(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log a user logout event."""
        return await self.log(
            action=AuditAction.LOGOUT,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_integration_connect(
        self,
        user_id: UUID,
        provider: str,
        scopes: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log an integration connection event."""
        action = {
            "gmail": AuditAction.GMAIL_CONNECT,
            "slack": AuditAction.SLACK_CONNECT,
        }.get(provider, f"{provider}_connect")

        return await self.log(
            action=action,
            user_id=user_id,
            details={"provider": provider, "scopes": scopes or []},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_integration_disconnect(
        self,
        user_id: UUID,
        provider: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log an integration disconnection event."""
        action = {
            "gmail": AuditAction.GMAIL_DISCONNECT,
            "slack": AuditAction.SLACK_DISCONNECT,
        }.get(provider, f"{provider}_disconnect")

        return await self.log(
            action=action,
            user_id=user_id,
            details={"provider": provider},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_security_event(
        self,
        action: str,
        user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log a security-related event (invalid token, rate limit, etc)."""
        return await self.log(
            action=action,
            user_id=user_id,
            details={"reason": reason} if reason else {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def get_user_logs(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
        actions: Optional[List[str]] = None,
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific user.

        Args:
            user_id: The user's ID
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            actions: Filter by specific actions

        Returns:
            List of AuditLog entries
        """
        query = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if actions:
            query = query.where(AuditLog.action.in_(actions))

        result = await self.db.execute(query)
        return list(result.scalars().all())
