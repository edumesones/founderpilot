# FEAT-002: Billing & Plans - Technical Design

## Overview

Sistema de billing basado en Stripe para gestión de suscripciones, trials, y overage. Arquitectura webhook-driven para mantener sincronización en tiempo real entre Stripe y la base de datos local.

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BILLING SYSTEM                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌───────────────┐         ┌───────────────┐         ┌───────────────┐        │
│   │    FRONTEND   │         │    BACKEND    │         │    STRIPE     │        │
│   │   (Next.js)   │         │   (FastAPI)   │         │   (External)  │        │
│   └───────┬───────┘         └───────┬───────┘         └───────┬───────┘        │
│           │                         │                         │                 │
│           │ GET /billing/subscription                         │                 │
│           │──────────────────────►│                           │                 │
│           │                       │                           │                 │
│           │ POST /billing/checkout                            │                 │
│           │──────────────────────►│                           │                 │
│           │                       │ create checkout session   │                 │
│           │                       │──────────────────────────►│                 │
│           │                       │◄──────────────────────────│                 │
│           │◄──────────────────────│ checkout_url              │                 │
│           │                       │                           │                 │
│           │ redirect to Stripe    │                           │                 │
│           │──────────────────────────────────────────────────►│                 │
│           │                       │                           │                 │
│           │                       │ webhook: checkout.completed                 │
│           │                       │◄──────────────────────────│                 │
│           │                       │ update subscription       │                 │
│           │                       │                           │                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow - Subscription Lifecycle

```
1. TRIAL START (on user signup via FEAT-001)
   User registers → Create Stripe Customer → Create local Subscription (trial)

2. CHECKOUT (user subscribes)
   User clicks "Subscribe" → POST /billing/checkout → Stripe Checkout
   → User pays → Webhook: checkout.session.completed → Update subscription (active)

3. RENEWAL (automatic monthly)
   Stripe charges → Webhook: invoice.paid → Log invoice, keep active

4. PAYMENT FAILURE
   Stripe fails → Webhook: invoice.payment_failed → Update status (past_due)
   → Stripe retries 3x → If all fail: subscription canceled

5. CANCELLATION
   User cancels via Portal → Webhook: subscription.updated (cancel_at_period_end=true)
   → Period ends → Webhook: subscription.deleted → Update status (canceled)

6. PLAN CHANGE
   User changes plan via Portal → Webhook: subscription.updated → Sync new plan
```

---

## File Structure

### New Files to Create

```
src/
├── api/
│   └── v1/
│       └── billing.py           # Billing API endpoints
├── models/
│   └── billing.py               # Plan, Subscription, Invoice models
├── schemas/
│   └── billing.py               # Pydantic request/response schemas
├── services/
│   └── billing_service.py       # Business logic for billing
├── core/
│   └── stripe.py                # Stripe client configuration
└── utils/
    └── billing_helpers.py       # Helper functions (usage calc, etc)

tests/
├── unit/
│   ├── test_billing_models.py
│   └── test_billing_service.py
└── integration/
    └── test_billing_api.py

alembic/
└── versions/
    └── 002_billing_tables.py    # Database migration
```

### Files to Modify

| File | Changes |
|------|---------|
| `src/api/v1/__init__.py` | Import and include billing router |
| `src/core/config.py` | Add Stripe env vars |
| `requirements.txt` | Add `stripe` package |
| `.env.example` | Add Stripe configuration vars |

---

## Data Model

### Database Schema

```sql
-- Plans (synced from Stripe, read-only locally)
CREATE TABLE plans (
    id VARCHAR(50) PRIMARY KEY,          -- stripe_price_id
    stripe_product_id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_cents INTEGER NOT NULL,
    interval VARCHAR(20) NOT NULL,        -- 'month'
    agents_included JSONB NOT NULL,       -- ["inbox", "invoice", "meeting"]
    limits JSONB NOT NULL,                -- {"emails_per_month": 500, ...}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Subscriptions (one per tenant)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(50),    -- null during trial
    stripe_customer_id VARCHAR(50) NOT NULL,
    plan_id VARCHAR(50) REFERENCES plans(id),
    status VARCHAR(20) NOT NULL,           -- trial, active, past_due, canceled, expired
    trial_ends_at TIMESTAMP,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(tenant_id)
);

-- Invoices (history from Stripe webhooks)
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    subscription_id UUID REFERENCES subscriptions(id),
    stripe_invoice_id VARCHAR(50) UNIQUE NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'usd',
    status VARCHAR(20) NOT NULL,           -- draft, open, paid, void, uncollectible
    period_start TIMESTAMP,
    period_end TIMESTAMP,
    paid_at TIMESTAMP,
    hosted_invoice_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Webhook Events (for idempotency)
CREATE TABLE stripe_events (
    id VARCHAR(100) PRIMARY KEY,           -- stripe event id
    type VARCHAR(100) NOT NULL,
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_subscriptions_tenant ON subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_invoices_tenant ON invoices(tenant_id);
CREATE INDEX idx_invoices_status ON invoices(status);
```

### SQLAlchemy Models

```python
# src/models/billing.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from src.core.database import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(String(50), primary_key=True)  # stripe_price_id
    stripe_product_id = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String)
    price_cents = Column(Integer, nullable=False)
    interval = Column(String(20), nullable=False)
    agents_included = Column(JSON, nullable=False)
    limits = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    stripe_subscription_id = Column(String(50), nullable=True)
    stripe_customer_id = Column(String(50), nullable=False)
    plan_id = Column(String(50), ForeignKey("plans.id"), nullable=True)
    status = Column(String(20), nullable=False)  # trial, active, past_due, canceled, expired
    trial_ends_at = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    plan = relationship("Plan")
    tenant = relationship("Tenant")
    invoices = relationship("Invoice", back_populates="subscription")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True)
    stripe_invoice_id = Column(String(50), unique=True, nullable=False)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default="usd")
    status = Column(String(20), nullable=False)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    hosted_invoice_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    id = Column(String(100), primary_key=True)
    type = Column(String(100), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
```

---

## API Design

### Endpoints Implementation

```python
# src/api/v1/billing.py
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import stripe

from src.core.database import get_db
from src.core.auth import get_current_tenant
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

router = APIRouter(prefix="/billing", tags=["billing"])

@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(db: Session = Depends(get_db)):
    """List all available plans (public)."""
    service = BillingService(db)
    return service.get_active_plans()

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get current tenant subscription with usage."""
    service = BillingService(db)
    return service.get_subscription_with_usage(tenant.id)

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create Stripe Checkout session for subscription."""
    service = BillingService(db)
    checkout_url = service.create_checkout_session(
        tenant_id=tenant.id,
        price_id=request.price_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url
    )
    return CheckoutResponse(checkout_url=checkout_url)

@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Create Stripe Customer Portal session."""
    service = BillingService(db)
    portal_url = service.create_portal_session(
        tenant_id=tenant.id,
        return_url=f"https://app.founderpilot.com/settings/billing"
    )
    return PortalResponse(portal_url=portal_url)

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    service = BillingService(db)

    try:
        service.handle_webhook(payload, stripe_signature)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List tenant invoices."""
    service = BillingService(db)
    return service.get_invoices(tenant.id)

@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get current usage vs limits."""
    service = BillingService(db)
    return service.get_usage(tenant.id)
```

### Pydantic Schemas

```python
# src/schemas/billing.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class PlanResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price_cents: int
    interval: str
    agents_included: list[str]
    limits: dict

    class Config:
        from_attributes = True

class SubscriptionPlan(BaseModel):
    id: str
    name: str
    price: int
    agents: list[str]

class UsageData(BaseModel):
    emails_processed: int
    emails_limit: int
    invoices_processed: int
    invoices_limit: int
    meetings_processed: int
    meetings_limit: int

class SubscriptionData(BaseModel):
    id: str
    status: str
    plan: Optional[SubscriptionPlan]
    trial_ends_at: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool

class SubscriptionResponse(BaseModel):
    subscription: SubscriptionData
    usage: UsageData

class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str

class CheckoutResponse(BaseModel):
    checkout_url: str

class PortalResponse(BaseModel):
    portal_url: str

class InvoiceResponse(BaseModel):
    id: UUID
    stripe_invoice_id: str
    amount_cents: int
    status: str
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    paid_at: Optional[datetime]
    hosted_invoice_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class UsageResponse(BaseModel):
    emails_processed: int
    emails_limit: int
    emails_overage: int
    invoices_processed: int
    invoices_limit: int
    invoices_overage: int
    meetings_processed: int
    meetings_limit: int
    meetings_overage: int
    period_start: datetime
    period_end: datetime
```

---

## Service Layer

### BillingService

```python
# src/services/billing_service.py
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import stripe
from sqlalchemy.orm import Session

from src.core.config import settings
from src.models.billing import Plan, Subscription, Invoice, StripeEvent
from src.schemas.billing import SubscriptionResponse, UsageResponse

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

class BillingService:
    def __init__(self, db: Session):
        self.db = db

    # --- Plans ---
    def get_active_plans(self) -> list[Plan]:
        return self.db.query(Plan).filter(Plan.is_active == True).all()

    def sync_plans_from_stripe(self):
        """Sync plans from Stripe (run on startup or admin action)."""
        prices = stripe.Price.list(active=True, expand=["data.product"])
        for price in prices.data:
            # Update or create local plan
            ...

    # --- Subscription ---
    def get_subscription_with_usage(self, tenant_id: UUID) -> SubscriptionResponse:
        sub = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id
        ).first()

        if not sub:
            raise ValueError("No subscription found")

        usage = self._calculate_usage(tenant_id, sub)

        return SubscriptionResponse(
            subscription=SubscriptionData(
                id=sub.stripe_subscription_id or str(sub.id),
                status=sub.status,
                plan=SubscriptionPlan(...) if sub.plan else None,
                trial_ends_at=sub.trial_ends_at,
                current_period_end=sub.current_period_end,
                cancel_at_period_end=sub.cancel_at_period_end
            ),
            usage=usage
        )

    def create_trial_subscription(self, tenant_id: UUID, email: str) -> Subscription:
        """Create trial subscription when user signs up (called from FEAT-001)."""
        # 1. Create Stripe Customer
        customer = stripe.Customer.create(
            email=email,
            metadata={"tenant_id": str(tenant_id)}
        )

        # 2. Create local subscription in trial status
        trial_ends = datetime.utcnow() + timedelta(days=14)
        subscription = Subscription(
            tenant_id=tenant_id,
            stripe_customer_id=customer.id,
            status="trial",
            trial_ends_at=trial_ends,
            current_period_start=datetime.utcnow(),
            current_period_end=trial_ends
        )
        self.db.add(subscription)
        self.db.commit()

        return subscription

    # --- Checkout ---
    def create_checkout_session(
        self,
        tenant_id: UUID,
        price_id: str,
        success_url: str,
        cancel_url: str
    ) -> str:
        """Create Stripe Checkout session."""
        sub = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id
        ).first()

        if not sub:
            raise ValueError("No subscription found")

        session = stripe.checkout.Session.create(
            customer=sub.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            subscription_data={
                "metadata": {"tenant_id": str(tenant_id)}
            },
            allow_promotion_codes=True
        )

        return session.url

    # --- Portal ---
    def create_portal_session(self, tenant_id: UUID, return_url: str) -> str:
        """Create Stripe Customer Portal session."""
        sub = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id
        ).first()

        if not sub:
            raise ValueError("No subscription found")

        session = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=return_url
        )

        return session.url

    # --- Webhooks ---
    def handle_webhook(self, payload: bytes, signature: str):
        """Process Stripe webhook event."""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            raise ValueError(f"Invalid webhook: {e}")

        # Idempotency check
        if self._event_already_processed(event.id):
            return

        # Route to handler
        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
        }

        handler = handlers.get(event.type)
        if handler:
            handler(event.data.object)

        # Mark event as processed
        self._mark_event_processed(event.id, event.type)

    def _handle_checkout_completed(self, session):
        """Handle successful checkout - activate subscription."""
        tenant_id = session.metadata.get("tenant_id") or \
                    session.subscription_data.metadata.get("tenant_id")

        # Get subscription details from Stripe
        stripe_sub = stripe.Subscription.retrieve(session.subscription)

        # Update local subscription
        sub = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id
        ).first()

        if sub:
            sub.stripe_subscription_id = stripe_sub.id
            sub.plan_id = stripe_sub.items.data[0].price.id
            sub.status = "active"
            sub.trial_ends_at = None
            sub.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
            sub.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
            self.db.commit()

    def _handle_invoice_paid(self, invoice):
        """Handle successful payment."""
        # Find subscription by stripe_subscription_id
        sub = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == invoice.subscription
        ).first()

        if sub:
            # Ensure status is active
            sub.status = "active"

            # Log invoice
            inv = Invoice(
                tenant_id=sub.tenant_id,
                subscription_id=sub.id,
                stripe_invoice_id=invoice.id,
                amount_cents=invoice.amount_paid,
                status="paid",
                period_start=datetime.fromtimestamp(invoice.period_start),
                period_end=datetime.fromtimestamp(invoice.period_end),
                paid_at=datetime.utcnow(),
                hosted_invoice_url=invoice.hosted_invoice_url
            )
            self.db.add(inv)
            self.db.commit()

    def _handle_invoice_payment_failed(self, invoice):
        """Handle failed payment."""
        sub = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == invoice.subscription
        ).first()

        if sub:
            sub.status = "past_due"
            self.db.commit()
            # TODO: Send notification to user

    def _handle_subscription_updated(self, stripe_sub):
        """Handle subscription changes (plan change, cancellation scheduled)."""
        sub = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub.id
        ).first()

        if sub:
            sub.plan_id = stripe_sub.items.data[0].price.id
            sub.status = stripe_sub.status
            sub.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
            sub.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
            sub.cancel_at_period_end = stripe_sub.cancel_at_period_end
            if stripe_sub.canceled_at:
                sub.canceled_at = datetime.fromtimestamp(stripe_sub.canceled_at)
            self.db.commit()

    def _handle_subscription_deleted(self, stripe_sub):
        """Handle subscription cancellation."""
        sub = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub.id
        ).first()

        if sub:
            sub.status = "canceled"
            sub.canceled_at = datetime.utcnow()
            self.db.commit()

    # --- Usage ---
    def _calculate_usage(self, tenant_id: UUID, subscription: Subscription) -> UsageData:
        """Calculate current usage for tenant."""
        # TODO: Query from usage tracking tables (FEAT-008)
        # For now, return mock data
        return UsageData(
            emails_processed=0,
            emails_limit=500,
            invoices_processed=0,
            invoices_limit=50,
            meetings_processed=0,
            meetings_limit=30
        )

    def get_usage(self, tenant_id: UUID) -> UsageResponse:
        """Get detailed usage report."""
        sub = self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id
        ).first()

        if not sub:
            raise ValueError("No subscription found")

        # TODO: Calculate actual usage from FEAT-008
        return UsageResponse(
            emails_processed=0,
            emails_limit=500,
            emails_overage=0,
            invoices_processed=0,
            invoices_limit=50,
            invoices_overage=0,
            meetings_processed=0,
            meetings_limit=30,
            meetings_overage=0,
            period_start=sub.current_period_start or datetime.utcnow(),
            period_end=sub.current_period_end or (datetime.utcnow() + timedelta(days=30))
        )

    # --- Invoices ---
    def get_invoices(self, tenant_id: UUID) -> list[Invoice]:
        """Get tenant invoices."""
        return self.db.query(Invoice).filter(
            Invoice.tenant_id == tenant_id
        ).order_by(Invoice.created_at.desc()).all()

    # --- Helpers ---
    def _event_already_processed(self, event_id: str) -> bool:
        return self.db.query(StripeEvent).filter(
            StripeEvent.id == event_id
        ).first() is not None

    def _mark_event_processed(self, event_id: str, event_type: str):
        event = StripeEvent(id=event_id, type=event_type)
        self.db.add(event)
        self.db.commit()
```

---

## Dependencies

### New Packages

| Package | Version | Purpose |
|---------|---------|---------|
| stripe | ^7.0.0 | Stripe API client |

### Environment Variables

```env
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Stripe Price IDs (created in Stripe Dashboard)
STRIPE_PRICE_INBOX=price_xxx
STRIPE_PRICE_INVOICE=price_xxx
STRIPE_PRICE_MEETING=price_xxx
STRIPE_PRICE_BUNDLE=price_xxx
```

---

## Error Handling

| Error | HTTP Code | Response |
|-------|-----------|----------|
| Subscription not found | 404 | `{"detail": "No subscription found"}` |
| Invalid webhook signature | 400 | `{"detail": "Invalid webhook signature"}` |
| Stripe API error | 502 | `{"detail": "Payment provider error"}` |
| Plan not found | 404 | `{"detail": "Plan not found"}` |
| Already subscribed | 400 | `{"detail": "Already have active subscription"}` |

---

## Security Considerations

- [x] Webhook signature verification with `STRIPE_WEBHOOK_SECRET`
- [x] All endpoints except `/plans` require authentication
- [x] Tenant isolation via `tenant_id` in all queries
- [x] No credit card data stored locally (PCI compliance via Stripe)
- [x] Idempotent webhook processing via `stripe_events` table
- [x] Rate limiting on webhook endpoint (recommend: 100 req/min)

---

## Testing Strategy

| Type | Coverage Target | Tools |
|------|-----------------|-------|
| Unit | 80%+ | pytest, pytest-mock |
| Integration | Main flows | pytest + httpx + stripe-mock |
| Webhook | All events | stripe listen --forward-to |

### Test Scenarios

1. **Trial Creation** - User signs up, trial subscription created
2. **Checkout Flow** - User subscribes, payment processed
3. **Webhook Processing** - All 5 webhook types handled correctly
4. **Plan Change** - Upgrade/downgrade via portal
5. **Cancellation** - User cancels, access until period end
6. **Payment Failure** - Invoice fails, status updated
7. **Idempotency** - Duplicate webhook ignored

---

## Implementation Order

### Phase 1: Foundation (Backend Core)
1. Create database migration
2. Create SQLAlchemy models
3. Create Pydantic schemas
4. Configure Stripe client

### Phase 2: Service Layer
5. Implement BillingService core methods
6. Implement trial creation (integration with FEAT-001)
7. Implement checkout session creation
8. Implement portal session creation

### Phase 3: Webhooks
9. Implement webhook endpoint
10. Implement webhook handlers (5 events)
11. Add idempotency checking

### Phase 4: API Endpoints
12. Create billing router
13. Implement all endpoints
14. Add to main app

### Phase 5: Integration
15. Add Stripe env vars to config
16. Seed initial plans in DB
17. Integration with FEAT-001 (trial on signup)

### Phase 6: Testing
18. Unit tests for service
19. Integration tests for API
20. Webhook testing with stripe-mock

### Phase 7: Frontend (Minimal)
21. Billing settings page
22. Trial banner component
23. Pricing page

---

## Open Technical Questions

- [x] ¿Cómo manejar trial sin tarjeta? → Crear subscription local con status "trial", sin stripe_subscription_id
- [x] ¿Cómo verificar acceso a agentes? → Query subscription.plan.agents_included
- [ ] ¿Usar metered billing para overage? → Pendiente validar con Stripe docs
- [ ] ¿Frontend en Next.js o parte de dashboard existente? → Asume dashboard existente

---

## References

- [Stripe Subscriptions Guide](https://stripe.com/docs/billing/subscriptions/overview)
- [Stripe Checkout](https://stripe.com/docs/payments/checkout)
- [Stripe Customer Portal](https://stripe.com/docs/customer-management/portal-deep-dive)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [FastAPI + Stripe Integration](https://stripe.com/docs/payments/accept-a-payment?platform=web&lang=python)

---

*Created: 2026-01-31*
*Last updated: 2026-01-31*
*Approved: [ ] Pending*
