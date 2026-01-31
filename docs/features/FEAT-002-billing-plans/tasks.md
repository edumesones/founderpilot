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
| 1.1 | Create database migration | ✅ |
| 1.2 | Create SQLAlchemy models | ✅ |
| 1.3 | Create Pydantic schemas | ✅ |
| 1.4 | Configure Stripe client | ✅ |

### Detailed Tasks

- [x] **B1.1**: Create database migration `002_billing_tables.py`
  - [x] B1.1.1: Create `plans` table
  - [x] B1.1.2: Create `subscriptions` table
  - [x] B1.1.3: Create `invoices` table
  - [x] B1.1.4: Create `stripe_events` table
  - [x] B1.1.5: Add indexes

- [x] **B1.2**: Create models in `src/models/billing.py`
  - [x] B1.2.1: Plan model
  - [x] B1.2.2: Subscription model
  - [x] B1.2.3: Invoice model
  - [x] B1.2.4: StripeEvent model

- [x] **B1.3**: Create schemas in `src/schemas/billing.py`
  - [x] B1.3.1: PlanResponse
  - [x] B1.3.2: SubscriptionResponse, SubscriptionData, UsageData
  - [x] B1.3.3: CheckoutRequest, CheckoutResponse
  - [x] B1.3.4: PortalResponse
  - [x] B1.3.5: InvoiceResponse
  - [x] B1.3.6: UsageResponse

- [x] **B1.4**: Configure Stripe in `src/core/stripe.py`
  - [x] B1.4.1: Stripe client setup
  - [x] B1.4.2: Add Stripe env vars to config.py
  - [x] B1.4.3: Update .env.example

---

## Phase 2: Service Layer

| # | Task | Status |
|---|------|--------|
| 2.1 | Implement BillingService core | ✅ |
| 2.2 | Trial subscription creation | ✅ |
| 2.3 | Checkout session creation | ✅ |
| 2.4 | Portal session creation | ✅ |

### Detailed Tasks

- [x] **B2.1**: Create `src/services/billing_service.py`
  - [x] B2.1.1: BillingService class structure
  - [x] B2.1.2: `get_active_plans()` method
  - [x] B2.1.3: `get_subscription_with_usage()` method
  - [x] B2.1.4: `get_invoices()` method
  - [x] B2.1.5: `get_usage()` method

- [x] **B2.2**: Implement trial creation
  - [x] B2.2.1: `create_trial_subscription()` method
  - [x] B2.2.2: Create Stripe Customer via API
  - [x] B2.2.3: Create local Subscription with trial status

- [x] **B2.3**: Implement checkout
  - [x] B2.3.1: `create_checkout_session()` method
  - [x] B2.3.2: Validate subscription exists
  - [x] B2.3.3: Create Stripe Checkout Session

- [x] **B2.4**: Implement portal
  - [x] B2.4.1: `create_portal_session()` method
  - [x] B2.4.2: Create Stripe Billing Portal Session

---

## Phase 3: Webhooks

| # | Task | Status |
|---|------|--------|
| 3.1 | Webhook handler | ✅ |
| 3.2 | Event handlers (5 events) | ✅ |
| 3.3 | Idempotency checking | ✅ |

### Detailed Tasks

- [x] **B3.1**: Implement webhook handling
  - [x] B3.1.1: `handle_webhook()` method
  - [x] B3.1.2: Signature verification
  - [x] B3.1.3: Event routing

- [x] **B3.2**: Implement event handlers
  - [x] B3.2.1: `_handle_checkout_completed()` - Activate subscription
  - [x] B3.2.2: `_handle_invoice_paid()` - Log invoice, keep active
  - [x] B3.2.3: `_handle_invoice_payment_failed()` - Set past_due
  - [x] B3.2.4: `_handle_subscription_updated()` - Sync plan changes
  - [x] B3.2.5: `_handle_subscription_deleted()` - Set canceled

- [x] **B3.3**: Implement idempotency
  - [x] B3.3.1: `_event_already_processed()` method
  - [x] B3.3.2: `_mark_event_processed()` method

---

## Phase 4: API Endpoints

| # | Task | Status |
|---|------|--------|
| 4.1 | Create billing router | ✅ |
| 4.2 | Implement all endpoints | ✅ |
| 4.3 | Add to main app | ✅ |

### Detailed Tasks

- [x] **B4.1**: Create `src/api/v1/billing.py`
  - [x] B4.1.1: Router setup with prefix `/billing`

- [x] **B4.2**: Implement endpoints
  - [x] B4.2.1: GET `/plans` - List available plans
  - [x] B4.2.2: GET `/subscription` - Get current subscription
  - [x] B4.2.3: POST `/checkout` - Create checkout session
  - [x] B4.2.4: POST `/portal` - Create portal session
  - [x] B4.2.5: POST `/webhook` - Handle Stripe webhooks
  - [x] B4.2.6: GET `/invoices` - List tenant invoices
  - [x] B4.2.7: GET `/usage` - Get current usage

- [x] **B4.3**: Register router
  - [x] B4.3.1: Import billing router in `src/api/v1/__init__.py`
  - [x] B4.3.2: Include router in main app

---

## Phase 5: Integration

| # | Task | Status |
|---|------|--------|
| 5.1 | Environment configuration | ✅ |
| 5.2 | Seed initial plans | ✅ |
| 5.3 | Integration with FEAT-001 | ✅ |

### Detailed Tasks

- [x] **B5.1**: Environment setup
  - [x] B5.1.1: Add Stripe vars to `src/core/config.py`
  - [x] B5.1.2: Update `.env.example` with all Stripe vars
  - [x] B5.1.3: Add `stripe` to `requirements.txt`

- [x] **B5.2**: Seed plans
  - [x] B5.2.1: Create seed script for plans
  - [x] B5.2.2: Define 4 plans (InboxPilot, InvoicePilot, MeetingPilot, Bundle)

- [x] **B5.3**: FEAT-001 integration (stub)
  - [x] B5.3.1: Export `create_trial_subscription` for auth module
  - [x] B5.3.2: Document integration point for FEAT-001 (placeholder auth dependency)

---

## Phase 6: Testing

| # | Task | Status |
|---|------|--------|
| 6.1 | Unit tests - models | ⬜ |
| 6.2 | Unit tests - service | ✅ |
| 6.3 | Integration tests - API | ⬜ |
| 6.4 | Webhook tests | ⬜ |

### Detailed Tasks

- [ ] **T6.1**: Create `tests/unit/test_billing_models.py`
  - [ ] T6.1.1: Test Plan model
  - [ ] T6.1.2: Test Subscription model
  - [ ] T6.1.3: Test Invoice model

- [x] **T6.2**: Create `tests/unit/test_billing_service.py`
  - [x] T6.2.1: Test get_active_plans
  - [x] T6.2.2: Test create_trial_subscription (mock Stripe)
  - [x] T6.2.3: Test create_checkout_session (mock Stripe)
  - [x] T6.2.4: Test webhook handlers (partial)

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
| 7.1 | Billing settings page | ⏭️ |
| 7.2 | Trial banner | ⏭️ |
| 7.3 | Pricing page | ⏭️ |

### Detailed Tasks

- [⏭️] **F7.1**: Billing settings page - *Deferred to frontend sprint*
- [⏭️] **F7.2**: Trial banner component - *Deferred to frontend sprint*
- [⏭️] **F7.3**: Pricing page - *Deferred to frontend sprint*

---

## Documentation Tasks

- [ ] **D1**: Update README with billing feature docs
- [ ] **D2**: Add API documentation for billing endpoints
- [x] **D3**: Document Stripe configuration steps (in .env.example)

---

## DevOps Tasks

- [x] **O1**: Add Stripe environment variables to deployment config (.env.example)
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
| Phase 1: Foundation | 4 | 4 | 100% |
| Phase 2: Service | 4 | 4 | 100% |
| Phase 3: Webhooks | 3 | 3 | 100% |
| Phase 4: API | 3 | 3 | 100% |
| Phase 5: Integration | 3 | 3 | 100% |
| Phase 6: Testing | 1 | 4 | 25% |
| Phase 7: Frontend | 0 | 3 | 0% (skipped) |
| Docs | 1 | 3 | 33% |
| DevOps | 1 | 3 | 33% |
| **TOTAL** | **20** | **30** | **67%** |

---

## Notes

### Blockers
_None currently_

### Decisions Made During Implementation

- **Auth dependency stub**: Created placeholder `get_current_tenant` that raises 401. Will be replaced when FEAT-001 is implemented.
- **Frontend deferred**: Focused on backend implementation. Frontend billing UI will be added during frontend sprint.
- **Tests partial**: Basic unit tests for service layer created. Full integration and webhook tests pending.

### Technical Debt

- [ ] Replace auth stub with FEAT-001 implementation
- [ ] Add comprehensive webhook tests
- [ ] Add API integration tests
- [ ] Frontend billing components

---

*Last updated: 2026-01-31*
*Updated by: Ralph Loop (Autonomous)*
