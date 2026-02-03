"""Usage tracking API endpoints."""
from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import CurrentUser
from src.core.database import SessionLocal
from src.models.user import User
from src.schemas.usage import UsageStatsResponse
from src.services.usage_service import UsageService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_sync_db() -> Session:
    """Get synchronous database session for usage service."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


@router.get(
    "/usage",
    response_model=UsageStatsResponse,
    summary="Get usage statistics",
    description="Get current billing period usage statistics for the authenticated user",
    responses={
        200: {
            "description": "Usage statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                        "period_start": "2024-02-01T00:00:00Z",
                        "period_end": "2024-03-01T00:00:00Z",
                        "plan": {
                            "name": "Bundle",
                            "limits": {
                                "emails_per_month": 500,
                                "invoices_per_month": 50,
                                "meetings_per_month": 30,
                            },
                        },
                        "usage": {
                            "inbox": {
                                "count": 425,
                                "limit": 500,
                                "percentage": 85,
                                "overage": 0,
                                "overage_cost_cents": 0,
                            },
                            "invoice": {
                                "count": 52,
                                "limit": 50,
                                "percentage": 104,
                                "overage": 2,
                                "overage_cost_cents": 20,
                            },
                            "meeting": {
                                "count": 15,
                                "limit": 30,
                                "percentage": 50,
                                "overage": 0,
                                "overage_cost_cents": 0,
                            },
                        },
                        "total_overage_cost_cents": 20,
                        "alerts": [
                            {
                                "agent": "inbox",
                                "message": "You've used 85% of your email quota this month",
                                "level": "warning",
                            },
                            {
                                "agent": "invoice",
                                "message": "You've exceeded your invoice quota. Extra charges: $0.20",
                                "level": "error",
                            },
                        ],
                    }
                }
            },
        },
        401: {"description": "Not authenticated"},
        403: {"description": "Subscription not active"},
        404: {"description": "No subscription found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def get_usage_stats(
    current_user: CurrentUser,
) -> UsageStatsResponse:
    """
    Get usage statistics for the current user's tenant.

    Returns comprehensive usage data including:
    - Current usage count per agent
    - Plan limits
    - Usage percentage
    - Overage amount and cost
    - Usage alerts (warnings and errors)

    **Authentication required**: JWT token via Authorization header or cookie

    **Rate limit**: 10 requests/minute per tenant
    """
    # Create sync database session
    db = SessionLocal()
    try:
        # Initialize usage service
        usage_service = UsageService(db)

        # Get usage stats for user's tenant
        # Note: Using user.id as tenant_id (single-user tenant model)
        tenant_id = current_user.id

        logger.info(
            "Fetching usage stats",
            extra={
                "user_id": str(current_user.id),
                "email": current_user.email,
                "tenant_id": str(tenant_id),
            },
        )

        stats = usage_service.get_usage_stats(tenant_id)

        logger.info(
            "Usage stats retrieved successfully",
            extra={
                "tenant_id": str(tenant_id),
                "total_overage": stats.total_overage_cost_cents,
                "alert_count": len(stats.alerts),
            },
        )

        return stats

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch usage stats",
            extra={
                "user_id": str(current_user.id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics",
        )
    finally:
        db.close()
