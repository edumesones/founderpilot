"""
Agent audit API routes for viewing AI agent action logs.

This module provides endpoints for:
- Listing audit logs with filters and pagination
- Getting detailed information for a specific audit log entry
- Exporting audit logs to CSV
- Getting audit statistics
"""

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, DbSession
from src.models.user import User
from src.schemas.agent_audit import (
    AgentAuditLogDetail,
    AgentAuditLogFilters,
    AgentAuditLogListResponse,
    AgentAuditStatsResponse,
)
from src.services.agent_audit import AgentAuditService


router = APIRouter(prefix="/api/v1/audit", tags=["agent-audit"])


async def get_agent_audit_service(db: DbSession) -> AgentAuditService:
    """Get agent audit service instance."""
    return AgentAuditService(db)


@router.get("", response_model=AgentAuditLogListResponse)
async def get_audit_logs(
    current_user: CurrentUser,
    service: Annotated[AgentAuditService, Depends(get_agent_audit_service)],
    agent: Optional[str] = Query(
        None,
        description="Filter by agent type (inbox_pilot, invoice_pilot, meeting_pilot)",
    ),
    from_date: Optional[datetime] = Query(
        None,
        alias="from",
        description="Start date filter (ISO 8601)",
    ),
    to_date: Optional[datetime] = Query(
        None,
        alias="to",
        description="End date filter (ISO 8601)",
    ),
    min_confidence: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence level",
    ),
    escalated: Optional[bool] = Query(
        None,
        description="Filter by escalation status",
    ),
    search: Optional[str] = Query(
        None,
        max_length=200,
        description="Full-text search in input/output",
    ),
    cursor: Optional[UUID] = Query(
        None,
        description="Pagination cursor (last entry ID)",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum entries to return",
    ),
) -> AgentAuditLogListResponse:
    """
    Get audit logs with filters and pagination.

    Returns a list of audit log entries for the authenticated user,
    with optional filters for agent type, date range, confidence level,
    escalation status, and text search.

    Uses cursor-based pagination for efficient querying of large datasets.
    """
    logs, next_cursor, has_more = await service.get_logs(
        user_id=current_user.id,
        limit=limit,
        cursor=cursor,
        agent_type=agent,
        escalated=escalated,
        min_confidence=min_confidence,
        from_date=from_date,
        to_date=to_date,
        search=search,
    )

    return AgentAuditLogListResponse(
        entries=logs,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/{log_id}", response_model=AgentAuditLogDetail)
async def get_audit_log_detail(
    log_id: UUID,
    current_user: CurrentUser,
    service: Annotated[AgentAuditService, Depends(get_agent_audit_service)],
) -> AgentAuditLogDetail:
    """
    Get detailed information for a specific audit log entry.

    Returns the full audit log entry including metadata, input/output data,
    and trace information. Only returns logs owned by the authenticated user.
    """
    log = await service.get_log_by_id(log_id, current_user.id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )

    return log


@router.get("/stats/summary", response_model=AgentAuditStatsResponse)
async def get_audit_stats(
    current_user: CurrentUser,
    service: Annotated[AgentAuditService, Depends(get_agent_audit_service)],
) -> AgentAuditStatsResponse:
    """
    Get statistics about agent actions for the authenticated user.

    Returns:
    - Total number of actions
    - Actions by agent type
    - Escalation count and rate
    - Average confidence level
    """
    stats = await service.get_stats(current_user.id)

    return AgentAuditStatsResponse(**stats)


@router.post("/{log_id}/rollback")
async def rollback_audit_log(
    log_id: UUID,
    current_user: CurrentUser,
    service: Annotated[AgentAuditService, Depends(get_agent_audit_service)],
) -> dict:
    """
    Mark an audit log entry as rolled back.

    This endpoint marks the action as rolled back but does not
    perform the actual rollback operation. The compensating action
    (e.g., unsend email, cancel reminder) should be triggered separately.

    This is a placeholder for MVP - full rollback functionality will be
    implemented post-MVP.
    """
    log = await service.mark_rolled_back(log_id, current_user.id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )

    return {
        "success": True,
        "message": "Audit log marked as rolled back",
        "log_id": str(log.id),
    }
