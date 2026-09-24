"""
Integration-related Pydantic schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from src.schemas.common import BaseSchema


class IntegrationStatus(BaseSchema):
    """Status of a single integration."""

    provider: str
    connected: bool
    connected_at: Optional[datetime] = None
    status: str = Field(..., description="active, expired, revoked, or disconnected")
    scopes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntegrationsStatusResponse(BaseSchema):
    """Response schema for integration status endpoint."""

    gmail: IntegrationStatus
    slack: IntegrationStatus
    all_connected: bool = Field(..., description="True if all required integrations are connected")


class IntegrationConnect(BaseSchema):
    """Response for initiating integration connection."""

    auth_url: str
    state: str


class IntegrationCallback(BaseSchema):
    """Data from integration OAuth callback."""

    code: str
    state: str
    error: Optional[str] = None
    error_description: Optional[str] = None


class DisconnectResponse(BaseSchema):
    """Response schema for disconnect endpoint."""

    provider: str
    message: str = "Successfully disconnected"
