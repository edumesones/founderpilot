"""
Audit log model for tracking user actions.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDMixin


class AuditLog(Base, UUIDMixin):
    """
    Audit log model for tracking security-relevant user actions.

    Attributes:
        id: Unique identifier (UUID)
        user_id: FK to the user (nullable for pre-auth events)
        action: Action performed (signup, login, gmail_connect, etc)
        details: Additional action-specific details
        ip_address: Client IP address
        user_agent: Client user agent string
        created_at: When the action occurred
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"


# Audit action constants
class AuditAction:
    """Constants for audit log actions."""

    # Auth actions
    SIGNUP = "signup"
    LOGIN = "login"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKE = "token_revoke"

    # Integration actions
    GMAIL_CONNECT = "gmail_connect"
    GMAIL_DISCONNECT = "gmail_disconnect"
    GMAIL_REFRESH = "gmail_refresh"
    SLACK_CONNECT = "slack_connect"
    SLACK_DISCONNECT = "slack_disconnect"

    # Onboarding actions
    ONBOARDING_COMPLETE = "onboarding_complete"

    # Security actions
    INVALID_TOKEN = "invalid_token"
    RATE_LIMITED = "rate_limited"
    OAUTH_ERROR = "oauth_error"
