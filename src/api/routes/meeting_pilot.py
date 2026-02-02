"""MeetingPilot API routes."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.meeting_pilot.config import (
    MeetingPilotConfigResponse,
    MeetingPilotConfigUpdate,
)
from src.schemas.meeting_pilot.meeting import (
    MeetingRecordResponse,
    MeetingNoteCreate,
    MeetingNoteResponse,
)
from src.services.meeting_pilot.service import MeetingPilotService

router = APIRouter()


# Response models

class MeetingListResponse(BaseModel):
    """Response for meeting list endpoint."""

    items: list[MeetingRecordResponse]
    total: int
    page: int
    limit: int
    has_more: bool


class MeetingDetailResponse(MeetingRecordResponse):
    """Response for meeting detail with notes."""

    notes: list[MeetingNoteResponse] = []


class SyncResponse(BaseModel):
    """Response for sync endpoint."""

    success: bool
    meetings_synced: int
    message: str


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: str
    last_sync_at: Optional[datetime] = None
    sync_healthy: bool
    meetings_pending: int
    meetings_processed_today: int


# Dependencies

# TODO: Add proper auth dependency
async def get_current_user_id() -> UUID:
    """Get current user ID from JWT token.

    This is a placeholder - implement proper auth.
    """
    # Placeholder user ID for development
    return UUID("00000000-0000-0000-0000-000000000001")


async def get_current_tenant_id() -> UUID:
    """Get current tenant ID from JWT token."""
    return UUID("00000000-0000-0000-0000-000000000001")


def get_service(db: AsyncSession = Depends(get_db)) -> MeetingPilotService:
    """Dependency to get MeetingPilotService."""
    return MeetingPilotService(db=db)


# Config endpoints


@router.get("/config", response_model=MeetingPilotConfigResponse)
async def get_config(
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingPilotService = Depends(get_service),
):
    """Get current MeetingPilot configuration."""
    config = await service.get_config(user_id)

    if not config:
        # Create default config
        config = await service.create_or_update_config(user_id, {})

    return config


@router.put("/config", response_model=MeetingPilotConfigResponse)
async def update_config(
    updates: MeetingPilotConfigUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingPilotService = Depends(get_service),
):
    """Update MeetingPilot configuration."""
    config = await service.create_or_update_config(
        user_id=user_id,
        config_data=updates.model_dump(exclude_unset=True),
    )
    return config


# Meeting endpoints


@router.get("/meetings", response_model=MeetingListResponse)
async def list_meetings(
    status: Optional[str] = Query(None, description="Filter by status"),
    days_ahead: int = Query(7, ge=1, le=30, description="Days to look ahead"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingPilotService = Depends(get_service),
):
    """List upcoming meetings."""
    # Get upcoming meetings for the next N days
    minutes_ahead = days_ahead * 24 * 60

    meetings = await service.get_upcoming_meetings(
        user_id=user_id,
        minutes_ahead=minutes_ahead,
        only_pending=status == "pending" if status else False,
    )

    # Apply pagination
    total = len(meetings)
    start = (page - 1) * limit
    end = start + limit
    paginated = meetings[start:end]

    return MeetingListResponse(
        items=[MeetingRecordResponse.model_validate(m) for m in paginated],
        total=total,
        page=page,
        limit=limit,
        has_more=end < total,
    )


@router.get("/meetings/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingPilotService = Depends(get_service),
):
    """Get a specific meeting with brief and notes."""
    meeting = await service.get_meeting(meeting_id)

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get meeting notes
    notes = await service.get_meeting_notes(meeting_id)

    return MeetingDetailResponse(
        **MeetingRecordResponse.model_validate(meeting).model_dump(),
        notes=[MeetingNoteResponse.model_validate(n) for n in notes],
    )


@router.post("/meetings/{meeting_id}/notes", response_model=MeetingNoteResponse)
async def add_note(
    meeting_id: UUID,
    note_data: MeetingNoteCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingPilotService = Depends(get_service),
):
    """Add a note to a meeting."""
    meeting = await service.get_meeting(meeting_id)

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    note = await service.add_note(
        meeting_id=meeting_id,
        user_id=user_id,
        note_data=note_data,
    )

    return note


@router.post("/meetings/{meeting_id}/complete")
async def complete_meeting(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingPilotService = Depends(get_service),
):
    """Mark a meeting as completed."""
    meeting = await service.get_meeting(meeting_id)

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await service.complete_meeting(meeting_id, "completed")

    return {"success": True, "message": "Meeting marked as completed"}


@router.post("/meetings/{meeting_id}/skip")
async def skip_meeting(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingPilotService = Depends(get_service),
):
    """Skip a meeting brief."""
    meeting = await service.get_meeting(meeting_id)

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await service.complete_meeting(meeting_id, "skipped")

    return {"success": True, "message": "Meeting brief skipped"}


# Sync endpoints


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    user_id: UUID = Depends(get_current_user_id),
    tenant_id: UUID = Depends(get_current_tenant_id),
    service: MeetingPilotService = Depends(get_service),
):
    """Trigger manual calendar sync."""
    try:
        # Note: In production, this would use the user's Calendar client
        # For now, we just queue the sync task
        from src.workers.tasks.meeting_tasks import sync_all_calendars

        # Queue async sync
        sync_all_calendars.delay()

        return SyncResponse(
            success=True,
            meetings_synced=0,  # Will be updated when task completes
            message="Calendar sync queued",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health endpoints


@router.get("/health", response_model=HealthResponse)
async def health_check(
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingPilotService = Depends(get_service),
):
    """Check MeetingPilot health status."""
    config = await service.get_config(user_id)

    if not config:
        return HealthResponse(
            status="not_configured",
            last_sync_at=None,
            sync_healthy=False,
            meetings_pending=0,
            meetings_processed_today=0,
        )

    # Check sync health (healthy if synced in last 30 minutes)
    sync_healthy = False
    if config.last_sync_at:
        sync_age = datetime.utcnow() - config.last_sync_at
        sync_healthy = sync_age < timedelta(minutes=30)

    # Get pending meetings count
    pending_meetings = await service.get_meetings_needing_briefs(user_id)

    return HealthResponse(
        status="healthy" if config.is_enabled and sync_healthy else "degraded",
        last_sync_at=config.last_sync_at,
        sync_healthy=sync_healthy,
        meetings_pending=len(pending_meetings),
        meetings_processed_today=config.total_meetings_processed,  # TODO: Track daily
    )
