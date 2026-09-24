"""Billing models for subscriptions, plans, and invoices."""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base


class Plan(Base):
    """Plan model - synced from Stripe Products/Prices."""

    __tablename__ = "plans"

    # A Plan *is* a Stripe Price: its identity is the Stripe price id, which is
    # what Stripe hands back in subscription.items[].price.id and what
    # Subscription.plan_id stores.
    stripe_price_id = Column(String(50), primary_key=True)
    stripe_product_id = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price_cents = Column(Integer, nullable=False)
    interval = Column(String(20), nullable=False, default="month")
    agents_included = Column(JSONB, nullable=False)  # ["inbox", "invoice", "meeting"]
    limits = Column(JSONB, nullable=False)  # {"emails_per_month": 500, ...}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Plan {self.name} ({self.stripe_price_id})>"


class Subscription(Base):
    """Subscription model - one per tenant."""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Tenant isolation: user = tenant (see src/models/user.py)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    stripe_subscription_id = Column(String(50), nullable=True)  # null during trial
    stripe_customer_id = Column(String(50), nullable=False)
    plan_id = Column(
        String(50), ForeignKey("plans.stripe_price_id"), nullable=True
    )
    status = Column(String(20), nullable=False)  # trial, active, past_due, canceled, expired
    trial_ends_at = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    plan = relationship("Plan", lazy="joined")
    invoices = relationship(
        "StripeInvoice", back_populates="subscription", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Subscription {self.id} ({self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if subscription allows access to agents."""
        return self.status in ("trial", "active")

    @property
    def days_remaining_in_trial(self) -> Optional[int]:
        """Get days remaining in trial, or None if not in trial."""
        if self.status != "trial" or not self.trial_ends_at:
            return None
        delta = self.trial_ends_at - datetime.utcnow()
        return max(0, delta.days)


class StripeInvoice(Base):
    """Stripe invoice model - payment history from Stripe webhooks.

    Named `stripe_invoices` to avoid colliding with the InvoicePilot `invoices`
    table (src/models/invoice_pilot/invoice.py), which tracks invoices the agent
    detects in Gmail. These are two different concepts.
    """

    __tablename__ = "stripe_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Tenant isolation: user = tenant (see src/models/user.py)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subscription_id = Column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True
    )
    stripe_invoice_id = Column(String(50), unique=True, nullable=False)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default="usd")
    status = Column(String(20), nullable=False)  # draft, open, paid, void, uncollectible
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    hosted_invoice_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")

    def __repr__(self) -> str:
        return f"<StripeInvoice {self.stripe_invoice_id} (${self.amount_cents/100})>"


class StripeEvent(Base):
    """Stripe event log for idempotency checking."""

    __tablename__ = "stripe_events"

    id = Column(String(100), primary_key=True)  # Stripe event ID
    type = Column(String(100), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<StripeEvent {self.id} ({self.type})>"
