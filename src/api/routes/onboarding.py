"""
Onboarding routes for tracking user setup progress.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import (
    ClientIP,
    CurrentUser,
    DbSession,
    RedisClient,
    UserAgent,
)
from src.models.audit_log import AuditAction
from src.schemas.onboarding import (
    OnboardingCompleteResponse,
    OnboardingStatus,
    OnboardingStep,
)
from src.services.audit import AuditService
from src.services.integration import IntegrationService


router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatus)
async def get_onboarding_status(
    current_user: CurrentUser,
    db: DbSession,
    redis_client: RedisClient,
):
    """
    Get current onboarding progress.

    Returns the status of each onboarding step and overall completion.
    """
    integration_service = IntegrationService(db, redis_client)
    integrations = await integration_service.get_status(current_user.id)

    # Define steps
    steps = [
        OnboardingStep(
            step="google",
            name="Google Account",
            completed=True,  # Always completed if user is authenticated
            current=False,
        ),
        OnboardingStep(
            step="gmail",
            name="Connect Gmail",
            completed=integrations.gmail.connected,
            current=not integrations.gmail.connected,
        ),
        OnboardingStep(
            step="slack",
            name="Connect Slack",
            completed=integrations.slack.connected,
            current=integrations.gmail.connected and not integrations.slack.connected,
        ),
    ]

    # Determine current step
    current_step = 1
    if integrations.gmail.connected:
        current_step = 2
    if integrations.gmail.connected and integrations.slack.connected:
        current_step = 3

    # Mark current step
    for i, step in enumerate(steps):
        step.current = (i + 1 == current_step) and not step.completed

    return OnboardingStatus(
        completed=current_user.onboarding_completed,
        current_step=current_step,
        steps=steps,
    )


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    current_user: CurrentUser,
    db: DbSession,
    redis_client: RedisClient,
    ip_address: ClientIP,
    user_agent: UserAgent,
):
    """
    Mark onboarding as complete.

    Can be called after all integrations are connected, or to skip
    remaining steps and complete anyway.
    """
    # Check if already completed
    if current_user.onboarding_completed:
        return OnboardingCompleteResponse(
            message="Onboarding already completed",
            redirect_url="/dashboard",
        )

    # Get integration status
    integration_service = IntegrationService(db, redis_client)
    integrations = await integration_service.get_status(current_user.id)

    # Optionally enforce all connections (or allow skip)
    # For MVP, we allow completing even without all connections
    # if not integrations.all_connected:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Please connect all integrations before completing onboarding",
    #     )

    # Mark onboarding as complete
    current_user.onboarding_completed = True
    current_user.updated_at = datetime.now(timezone.utc)

    await db.flush()

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action=AuditAction.ONBOARDING_COMPLETE,
        user_id=current_user.id,
        details={
            "gmail_connected": integrations.gmail.connected,
            "slack_connected": integrations.slack.connected,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return OnboardingCompleteResponse(
        message="Onboarding completed successfully",
        redirect_url="/dashboard",
    )


@router.post("/skip")
async def skip_onboarding(
    current_user: CurrentUser,
    db: DbSession,
    ip_address: ClientIP,
    user_agent: UserAgent,
):
    """
    Skip onboarding entirely.

    Marks onboarding as complete without requiring integrations.
    User can connect integrations later from settings.
    """
    # Mark as complete
    current_user.onboarding_completed = True
    current_user.updated_at = datetime.now(timezone.utc)

    await db.flush()

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action=AuditAction.ONBOARDING_COMPLETE,
        user_id=current_user.id,
        details={"skipped": True},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return {
        "message": "Onboarding skipped",
        "redirect_url": "/dashboard",
    }
