"""Pydantic schemas for billing API requests and responses."""
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field


# --- Plan Schemas ---


class PlanResponse(BaseModel):
    """Response schema for plan data."""

    id: str
    name: str
    description: Optional[str] = None
    price_cents: int
    interval: str
    agents_included: list[str]
    limits: dict[str, Any]

    class Config:
        from_attributes = True


# --- Subscription Schemas ---


class SubscriptionPlan(BaseModel):
    """Embedded plan data in subscription response."""

    id: str
    name: str
    price: int = Field(description="Price in cents")
    agents: list[str] = Field(description="Agents included in plan")


class UsageData(BaseModel):
    """Current usage data for subscription."""

    emails_processed: int = 0
    emails_limit: int = 500
    invoices_processed: int = 0
    invoices_limit: int = 50
    meetings_processed: int = 0
    meetings_limit: int = 30


class SubscriptionData(BaseModel):
    """Subscription details."""

    id: str
    status: str = Field(description="trial, active, past_due, canceled, expired")
    plan: Optional[SubscriptionPlan] = None
    trial_ends_at: Optional[datetime] = None
    trial_days_remaining: Optional[int] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False


class SubscriptionResponse(BaseModel):
    """Response schema for subscription with usage."""

    subscription: SubscriptionData
    usage: UsageData


# --- Checkout Schemas ---


class CheckoutRequest(BaseModel):
    """Request schema for creating a checkout session."""

    price_id: str = Field(description="Stripe price ID to subscribe to")
    success_url: str = Field(description="URL to redirect after successful payment")
    cancel_url: str = Field(description="URL to redirect if payment is cancelled")


class CheckoutResponse(BaseModel):
    """Response schema with Stripe checkout URL."""

    checkout_url: str


# --- Portal Schemas ---


class PortalResponse(BaseModel):
    """Response schema with Stripe customer portal URL."""

    portal_url: str


# --- Invoice Schemas ---


class InvoiceResponse(BaseModel):
    """Response schema for invoice data."""

    id: UUID
    stripe_invoice_id: str
    amount_cents: int
    currency: str = "usd"
    status: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    hosted_invoice_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Usage Schemas ---


class UsageResponse(BaseModel):
    """Detailed usage response with overage information."""

    emails_processed: int
    emails_limit: int
    emails_overage: int = 0
    invoices_processed: int
    invoices_limit: int
    invoices_overage: int = 0
    meetings_processed: int
    meetings_limit: int
    meetings_overage: int = 0
    period_start: datetime
    period_end: datetime
