"""InboxPilot API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.schemas.inbox_pilot.config import (
    InboxPilotConfigResponse,
    InboxPilotConfigUpdate,
    WatchSetupResponse,
)
from src.schemas.inbox_pilot.email import (
    EmailActionRequest,
    EmailActionResponse,
    EmailListResponse,
    EmailResponse,
)
from src.services.inbox_pilot.service import InboxPilotService

router = APIRouter()


# TODO: Add proper auth dependency
async def get_current_user_id() -> UUID:
    """Get current user ID from JWT token.

    This is a placeholder - implement proper auth.
    """
    # Placeholder user ID for development
    return UUID("00000000-0000-0000-0000-000000000001")


def get_service(db: AsyncSession = Depends(get_db)) -> InboxPilotService:
    """Dependency to get InboxPilotService."""
    return InboxPilotService(db=db)


# Config endpoints


@router.get("/config", response_model=InboxPilotConfigResponse)
async def get_config(
    user_id: UUID = Depends(get_current_user_id),
    service: InboxPilotService = Depends(get_service),
):
    """Get current InboxPilot configuration."""
    config = await service.get_or_create_config(user_id)
    return config


@router.put("/config", response_model=InboxPilotConfigResponse)
async def update_config(
    updates: InboxPilotConfigUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: InboxPilotService = Depends(get_service),
):
    """Update InboxPilot configuration."""
    config = await service.update_config(user_id, updates)
    return config


# Email endpoints


@router.get("/emails", response_model=EmailListResponse)
async def list_emails(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
    service: InboxPilotService = Depends(get_service),
):
    """List processed emails."""
    records, total = await service.list_emails(
        user_id=user_id,
        status=status,
        category=category,
        page=page,
        limit=limit,
    )

    return EmailListResponse(
        items=[EmailResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        limit=limit,
        has_more=(page * limit) < total,
    )


@router.get("/emails/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: InboxPilotService = Depends(get_service),
):
    """Get a specific email record."""
    record = await service.get_email(email_id)

    if not record:
        raise HTTPException(status_code=404, detail="Email not found")

    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return record


@router.post("/emails/{email_id}/action", response_model=EmailActionResponse)
async def take_action(
    email_id: UUID,
    action_request: EmailActionRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: InboxPilotService = Depends(get_service),
):
    """Take action on an email (approve, reject, archive, edit)."""
    record = await service.get_email(email_id)

    if not record:
        raise HTTPException(status_code=404, detail="Email not found")

    if record.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        updated = await service.handle_slack_action(
            message_id=record.gmail_message_id,
            action=action_request.action,
            edited_content=action_request.edited_content,
        )

        return EmailActionResponse(
            success=True,
            action_taken=updated.action_taken,
            message=f"Email {updated.action_taken}",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Watch endpoints


@router.post("/watch", response_model=WatchSetupResponse)
async def setup_watch(
    user_id: UUID = Depends(get_current_user_id),
    service: InboxPilotService = Depends(get_service),
):
    """Set up Gmail push notifications."""
    try:
        result = await service.setup_watch(user_id)

        return WatchSetupResponse(
            success=True,
            history_id=result["history_id"],
            expiration=result["expiration"],
            message="Gmail watch set up successfully",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watch")
async def stop_watch(
    user_id: UUID = Depends(get_current_user_id),
    service: InboxPilotService = Depends(get_service),
):
    """Stop Gmail push notifications."""
    try:
        await service.stop_watch(user_id)
        return {"success": True, "message": "Gmail watch stopped"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
