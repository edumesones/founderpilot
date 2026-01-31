"""Billing API endpoints."""
from typing import Any
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.config import settings
from src.services.billing_service import BillingService
from src.schemas.billing import (
    PlanResponse,
    SubscriptionResponse,
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    InvoiceResponse,
    UsageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# Placeholder for auth dependency from FEAT-001
# TODO: Replace with actual auth dependency when FEAT-001 is implemented
class TenantStub:
    """Stub for tenant from auth."""

    def __init__(self, id: UUID):
        self.id = id


async def get_current_tenant() -> TenantStub:
    """Placeholder auth dependency.

    TODO: Replace with actual implementation from FEAT-001.
    For now, returns a stub tenant for testing.
    """
    # In production, this would:
    # 1. Extract JWT from Authorization header
    # 2. Validate and decode JWT
    # 3. Return tenant from database
    raise HTTPException(
        status_code=401,
        detail="Authentication not implemented. Waiting for FEAT-001.",
    )


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(db: Session = Depends(get_db)) -> list[PlanResponse]:
    """List all available plans.

    This endpoint is public - no authentication required.
    """
    service = BillingService(db)
    return service.get_active_plans()


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    tenant: TenantStub = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Get current tenant subscription with usage information."""
    service = BillingService(db)
    try:
        return service.get_subscription_with_usage(tenant.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    tenant: TenantStub = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    """Create a Stripe Checkout session for subscription.

    Redirects user to Stripe's hosted checkout page.
    """
    service = BillingService(db)
    try:
        checkout_url = service.create_checkout_session(
            tenant_id=tenant.id,
            price_id=request.price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return CheckoutResponse(checkout_url=checkout_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    tenant: TenantStub = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> PortalResponse:
    """Create a Stripe Customer Portal session.

    Allows users to manage payment methods, view invoices, and change plans.
    """
    service = BillingService(db)
    return_url = f"{settings.FRONTEND_URL}/settings/billing"
    try:
        portal_url = service.create_portal_session(
            tenant_id=tenant.id,
            return_url=return_url,
        )
        return PortalResponse(portal_url=portal_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Handle Stripe webhook events.

    Processes events like:
    - checkout.session.completed
    - invoice.paid
    - invoice.payment_failed
    - customer.subscription.updated
    - customer.subscription.deleted
    """
    payload = await request.body()
    service = BillingService(db)

    try:
        service.handle_webhook(payload, stripe_signature)
        return {"status": "ok"}
    except ValueError as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    tenant: TenantStub = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> list[InvoiceResponse]:
    """List invoices for the current tenant."""
    service = BillingService(db)
    return service.get_invoices(tenant.id)


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    tenant: TenantStub = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> UsageResponse:
    """Get current usage vs plan limits.

    Shows:
    - Emails processed / limit
    - Invoices processed / limit
    - Meetings processed / limit
    - Overage amounts
    """
    service = BillingService(db)
    try:
        return service.get_usage(tenant.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
