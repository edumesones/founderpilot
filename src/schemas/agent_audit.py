"""
Pydantic schemas for Agent Audit API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.schemas.common import BaseSchema


class AgentAuditLogBase(BaseSchema):
    """Base schema for agent audit log."""

    timestamp: datetime
    agent_type: str = Field(..., max_length=50)
    action: str = Field(..., max_length=100)
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    decision: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    escalated: bool = False
    authorized_by: Optional[str] = Field(None, max_length=50)
    trace_id: Optional[str] = Field(None, max_length=255)
    rolled_back: bool = False


class AgentAuditLogListItem(AgentAuditLogBase):
    """Schema for audit log in list view (without full metadata)."""

    id: UUID
    user_id: UUID
    workflow_id: Optional[UUID] = None

    @field_validator("input_summary", "output_summary", mode="before")
    @classmethod
    def truncate_summaries(cls, v: Optional[str]) -> Optional[str]:
        """Truncate summaries to 500 chars for list view."""
        if v and len(v) > 500:
            return v[:497] + "..."
        return v


class AgentAuditLogDetail(AgentAuditLogBase):
    """Schema for full audit log detail (includes metadata)."""

    id: UUID
    user_id: UUID
    workflow_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AgentAuditLogListResponse(BaseModel):
    """Response schema for audit log list."""

    entries: List[AgentAuditLogListItem]
    next_cursor: Optional[UUID] = None
    has_more: bool


class AgentAuditLogFilters(BaseModel):
    """Query parameters for filtering audit logs."""

    agent: Optional[str] = Field(
        None,
        description="Filter by agent type (inbox_pilot, invoice_pilot, meeting_pilot)",
    )
    from_date: Optional[datetime] = Field(None, alias="from")
    to_date: Optional[datetime] = Field(None, alias="to")
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    escalated: Optional[bool] = None
    search: Optional[str] = Field(None, max_length=200)
    cursor: Optional[UUID] = None
    limit: int = Field(50, ge=1, le=100)

    model_config = {"populate_by_name": True}


class ExportFilters(BaseModel):
    """Filters for CSV export."""

    agent: Optional[str] = None
    from_date: Optional[datetime] = Field(None, alias="from")
    to_date: Optional[datetime] = Field(None, alias="to")

    model_config = {"populate_by_name": True}


class AgentAuditLogCreate(BaseModel):
    """Schema for creating an audit log entry (for internal use by agents)."""

    user_id: UUID
    agent_type: str = Field(..., max_length=50)
    action: str = Field(..., max_length=100)
    input_summary: Optional[str] = Field(None, max_length=2000)
    output_summary: Optional[str] = Field(None, max_length=2000)
    decision: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    escalated: bool = False
    authorized_by: Optional[str] = Field(None, max_length=50)
    trace_id: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict[str, Any]] = None
    workflow_id: Optional[UUID] = None


class AgentAuditStatsResponse(BaseModel):
    """Response schema for agent audit statistics."""

    total_actions: int
    by_agent: Dict[str, int]
    escalated_count: int
    escalation_rate: float
    average_confidence: Optional[float]


class ConfidenceLevel(BaseModel):
    """Schema for confidence level display."""

    value: float = Field(..., ge=0.0, le=1.0)
    label: str  # "Low", "Medium", "High"
    color: str  # "red", "yellow", "green"

    @staticmethod
    def from_confidence(confidence: Optional[float]) -> Optional["ConfidenceLevel"]:
        """Convert confidence float to ConfidenceLevel with label and color."""
        if confidence is None:
            return None

        if confidence >= 0.9:
            return ConfidenceLevel(
                value=confidence,
                label="High",
                color="green",
            )
        elif confidence >= 0.7:
            return ConfidenceLevel(
                value=confidence,
                label="Medium",
                color="yellow",
            )
        else:
            return ConfidenceLevel(
                value=confidence,
                label="Low",
                color="red",
            )
