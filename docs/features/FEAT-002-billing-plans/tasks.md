# FEAT-002: Billing & Plans - Tasks

## Pre-Implementation Checklist
- [x] spec.md complete and approved
- [x] design.md complete and approved
- [x] Branch created: `feat/FEAT-002`
- [x] status.md updated to "In Progress"

---

## Phase 1: Foundation (Backend Core)

| # | Task | Status |
|---|------|--------|
| 1.1 | Create database migration | ⬜ |
| 1.2 | Create SQLAlchemy models | ⬜ |
| 1.3 | Create Pydantic schemas | ⬜ |
| 1.4 | Configure Stripe client | ⬜ |

### Detailed Tasks

- [ ] **B1.1**: Create database migration `002_billing_tables.py`
  - [ ] B1.1.1: Create `plans` table
  - [ ] B1.1.2: Create `subscriptions` table
  - [ ] B1.1.3: Create `invoices` table
  - [ ] B1.1.4: Create `stripe_events` table
  - [ ] B1.1.5: Add indexes

- [ ] **B1.2**: Create models in `src/models/billing.py`
  - [ ] B1.2.1: Plan model
  - [ ] B1.2.2: Subscription model
  - [ ] B1.2.3: Invoice model
  - [ ] B1.2.4: StripeEvent model

- [ ] **B1.3**: Create schemas in `src/schemas/billing.py`
  - [ ] B1.3.1: PlanResponse
  - [ ] B1.3.2: SubscriptionResponse, SubscriptionData, UsageData
  - [ ] B1.3.3: CheckoutRequest, CheckoutResponse
  - [ ] B1.3.4: PortalResponse
  - [ ] B1.3.5: InvoiceResponse
  - [ ] B1.3.6: UsageResponse

- [ ] **B1.4**: Configure Stripe in `src/core/stripe.py`
  - [ ] B1.4.1: Stripe client setup
  - [ ] B1.4.2: Add Stripe env vars to config.py
  - [ ] B1.4.3: Update .env.example

---

## Phase 2: Service Layer

| # | Task | Status |
|---|------|--------|
| 2.1 | Implement BillingService core | ⬜ |
| 2.2 | Trial subscription creation | ⬜ |
| 2.3 | Checkout session creation | ⬜ |
| 2.4 | Portal session creation | ⬜ |

### Detailed Tasks

- [ ] **B2.1**: Create `src/services/billing_service.py`
  - [ ] B2.1.1: BillingService class structure
  - [ ] B2.1.2: `get_active_plans()` method
  - [ ] B2.1.3: `get_subscription_with_usage()` method
  - [ ] B2.1.4: `get_invoices()` method
  - [ ] B2.1.5: `get_usage()` method

- [ ] **B2.2**: Implement trial creation
  - [ ] B2.2.1: `create_trial_subscription()` method
  - [ ] B2.2.2: Create Stripe Customer via API
  - [ ] B2.2.3: Create local Subscription with trial status

- [ ] **B2.3**: Implement checkout
  - [ ] B2.3.1: `create_checkout_session()` method
  - [ ] B2.3.2: Validate subscription exists
  - [ ] B2.3.3: Create Stripe Checkout Session

- [ ] **B2.4**: Implement portal
  - [ ] B2.4.1: `create_portal_session()` method
  - [ ] B2.4.2: Create Stripe Billing Portal Session

---

## Phase 3: Webhooks

| # | Task | Status |
|---|------|--------|
| 3.1 | Webhook handler | ⬜ |
| 3.2 | Event handlers (5 events) | ⬜ |
| 3.3 | Idempotency checking | ⬜ |

### Detailed Tasks

- [ ] **B3.1**: Implement webhook handling
  - [ ] B3.1.1: `handle_webhook()` method
  - [ ] B3.1.2: Signature verification
  - [ ] B3.1.3: Event routing

- [ ] **B3.2**: Implement event handlers
  - [ ] B3.2.1: `_handle_checkout_completed()` - Activate subscription
  - [ ] B3.2.2: `_handle_invoice_paid()` - Log invoice, keep active
  - [ ] B3.2.3: `_handle_invoice_payment_failed()` - Set past_due
  - [ ] B3.2.4: `_handle_subscription_updated()` - Sync plan changes
  - [ ] B3.2.5: `_handle_subscription_deleted()` - Set canceled

- [ ] **B3.3**: Implement idempotency
  - [ ] B3.3.1: `_event_already_processed()` method
  - [ ] B3.3.2: `_mark_event_processed()` method

---

## Phase 4: API Endpoints

| # | Task | Status |
|---|------|--------|
| 4.1 | Create billing router | ⬜ |
| 4.2 | Implement all endpoints | ⬜ |
| 4.3 | Add to main app | ⬜ |

### Detailed Tasks

- [ ] **B4.1**: Create `src/api/v1/billing.py`
  - [ ] B4.1.1: Router setup with prefix `/billing`

- [ ] **B4.2**: Implement endpoints
  - [ ] B4.2.1: GET `/plans` - List available plans
  - [ ] B4.2.2: GET `/subscription` - Get current subscription
  - [ ] B4.2.3: POST `/checkout` - Create checkout session
  - [ ] B4.2.4: POST `/portal` - Create portal session
  - [ ] B4.2.5: POST `/webhook` - Handle Stripe webhooks
  - [ ] B4.2.6: GET `/invoices` - List tenant invoices
  - [ ] B4.2.7: GET `/usage` - Get current usage

- [ ] **B4.3**: Register router
  - [ ] B4.3.1: Import billing router in `src/api/v1/__init__.py`
  - [ ] B4.3.2: Include router in main app

---

## Phase 5: Integration

| # | Task | Status |
|---|------|--------|
| 5.1 | Environment configuration | ⬜ |
| 5.2 | Seed initial plans | ⬜ |
| 5.3 | Integration with FEAT-001 | ⬜ |

### Detailed Tasks

- [ ] **B5.1**: Environment setup
  - [ ] B5.1.1: Add Stripe vars to `src/core/config.py`
  - [ ] B5.1.2: Update `.env.example` with all Stripe vars
  - [ ] B5.1.3: Add `stripe` to `requirements.txt`

- [ ] **B5.2**: Seed plans
  - [ ] B5.2.1: Create seed script for plans
  - [ ] B5.2.2: Define 4 plans (InboxPilot, InvoicePilot, MeetingPilot, Bundle)

- [ ] **B5.3**: FEAT-001 integration (stub)
  - [ ] B5.3.1: Export `create_trial_subscription` for auth module
  - [ ] B5.3.2: Document integration point for FEAT-001

---

## Phase 6: Testing

| # | Task | Status |
|---|------|--------|
| 6.1 | Unit tests - models | ⬜ |
| 6.2 | Unit tests - service | ⬜ |
| 6.3 | Integration tests - API | ⬜ |
| 6.4 | Webhook tests | ⬜ |

### Detailed Tasks

- [ ] **T6.1**: Create `tests/unit/test_billing_models.py`
  - [ ] T6.1.1: Test Plan model
  - [ ] T6.1.2: Test Subscription model
  - [ ] T6.1.3: Test Invoice model

- [ ] **T6.2**: Create `tests/unit/test_billing_service.py`
  - [ ] T6.2.1: Test get_active_plans
  - [ ] T6.2.2: Test create_trial_subscription (mock Stripe)
  - [ ] T6.2.3: Test create_checkout_session (mock Stripe)
  - [ ] T6.2.4: Test webhook handlers

- [ ] **T6.3**: Create `tests/integration/test_billing_api.py`
  - [ ] T6.3.1: Test GET /plans
  - [ ] T6.3.2: Test GET /subscription
  - [ ] T6.3.3: Test POST /checkout
  - [ ] T6.3.4: Test POST /portal
  - [ ] T6.3.5: Test GET /invoices

- [ ] **T6.4**: Webhook integration tests
  - [ ] T6.4.1: Test checkout.session.completed
  - [ ] T6.4.2: Test invoice.paid
  - [ ] T6.4.3: Test invoice.payment_failed
  - [ ] T6.4.4: Test subscription.updated
  - [ ] T6.4.5: Test subscription.deleted
  - [ ] T6.4.6: Test idempotency (duplicate event)

---

## Phase 7: Frontend (Minimal)

| # | Task | Status |
|---|------|--------|
| 7.1 | Billing settings page | ⬜ |
| 7.2 | Trial banner | ⬜ |
| 7.3 | Pricing page | ⬜ |

### Detailed Tasks

- [ ] **F7.1**: Billing settings page
  - [ ] F7.1.1: Create `/settings/billing` route
  - [ ] F7.1.2: Show current plan and status
  - [ ] F7.1.3: Show usage vs limits
  - [ ] F7.1.4: Show invoices list
  - [ ] F7.1.5: "Manage Billing" button (portal link)

- [ ] **F7.2**: Trial banner component
  - [ ] F7.2.1: Show days remaining in trial
  - [ ] F7.2.2: CTA "Subscribe Now"
  - [ ] F7.2.3: Show in dashboard header when status=trial

- [ ] **F7.3**: Pricing page
  - [ ] F7.3.1: Create `/pricing` route
  - [ ] F7.3.2: 4 plan cards with features
  - [ ] F7.3.3: "Choose Plan" buttons trigger checkout

---

## Documentation Tasks

- [ ] **D1**: Update README with billing feature docs
- [ ] **D2**: Add API documentation for billing endpoints
- [ ] **D3**: Document Stripe configuration steps

---

## DevOps Tasks

- [ ] **O1**: Add Stripe environment variables to deployment config
- [ ] **O2**: Configure webhook endpoint in Stripe Dashboard
- [ ] **O3**: Set up stripe CLI for local webhook testing

---

## Progress Tracking

### Status Legend
| Symbol | Meaning |
|--------|---------|
| `- [ ]` | ⬜ Pending |
| `- [🟡]` | 🟡 In Progress |
| `- [x]` | ✅ Completed |
| `- [🔴]` | 🔴 Blocked |
| `- [⏭️]` | ⏭️ Skipped |

### Current Progress

| Section | Done | Total | % |
|---------|------|-------|---|
| Phase 1: Foundation | 0 | 4 | 0% |
| Phase 2: Service | 0 | 4 | 0% |
| Phase 3: Webhooks | 0 | 3 | 0% |
| Phase 4: API | 0 | 3 | 0% |
| Phase 5: Integration | 0 | 3 | 0% |
| Phase 6: Testing | 0 | 4 | 0% |
| Phase 7: Frontend | 0 | 3 | 0% |
| Docs | 0 | 3 | 0% |
| DevOps | 0 | 3 | 0% |
| **TOTAL** | **0** | **30** | **0%** |

---

## Notes

### Blockers
_None currently_

### Decisions Made During Implementation
_Document any decisions made while implementing_

### Technical Debt
_Track any shortcuts taken that need future work_

---

*Last updated: 2026-01-31*
*Updated by: Ralph Loop (Autonomous)*
