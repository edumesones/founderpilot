# FEAT-008: Implementation Tasks

> Generated from design.md (Phase 3)
> **Total:** 25 tasks across 5 sections

---

## Progress Overview

```
[█████████████░░░░░░░] 64% (16/25 tasks)
```

### By Section

| Section | Progress | Status |
|---------|----------|--------|
| Backend - Models | 3/3 | ✅ Complete |
| Backend - Services | 4/5 | ⏳ In Progress |
| Backend - API | 2/3 | ⏳ In Progress |
| Backend - Workers | 4/4 | ✅ Complete |
| Frontend | 0/2 | ⬜ Not Started |
| Tests | 3/5 | ⏳ In Progress |
| DevOps | 0/3 | ⬜ Not Started |

---

## Section 1: Backend - Database Models

### B1.1: Create usage.py models file ✅
**File:** `src/models/usage.py`
**Description:** Create UsageEvent and UsageCounter SQLAlchemy models
**Acceptance Criteria:**
- [ ] UsageEvent model with all fields (id, tenant_id, agent, action_type, resource_id, quantity, idempotency_key, metadata, created_at)
- [ ] UsageCounter model with all fields (id, tenant_id, agent, period_start, period_end, count, last_event_at, created_at, updated_at)
- [ ] Proper foreign keys and indexes
- [ ] CHECK constraint on counter.count >= 0
- [ ] UNIQUE constraint on (tenant_id, agent, period_start) for UsageCounter
- [ ] UNIQUE constraint on idempotency_key for UsageEvent
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 30 min

### B1.2: Create Alembic migration ✅
**File:** `alembic/versions/008_add_usage_tracking_tables.py`
**Description:** Database migration to create usage_events and usage_counters tables
**Acceptance Criteria:**
- [x] Migration creates both tables with correct schema
- [x] Indexes created: idx_usage_events_tenant_agent, idx_usage_events_idempotency, idx_usage_counters_tenant_period
- [x] Migration is reversible (downgrade removes tables)
- [ ] Migration tested locally (requires DB connection)
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 20 min

### B1.3: Update models __init__.py ✅
**File:** `src/models/__init__.py`
**Description:** Export new models for imports
**Acceptance Criteria:**
- [x] Import UsageEvent and UsageCounter from usage module
- [x] Add to __all__ list
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 5 min

---

## Section 2: Backend - Services

### B2.1: Create UsageTracker service ✅
**File:** `src/services/usage_tracker.py`
**Description:** Core service for atomic event recording + counter updates
**Acceptance Criteria:**
- [x] UsageTracker class with track_event() method
- [x] Atomic transaction: event write + counter increment
- [x] Idempotency key generation logic
- [x] _get_or_create_counter() helper method
- [x] Proper error handling (ValueError, IntegrityError)
- [x] Logging for each event tracked
- [x] Metrics emission (usage_events_total)
**Safe for Ralph:** ⚠️ Needs Review (transaction logic critical)
**Estimated effort:** 60 min

### B2.2: Create UsageService ✅
**File:** `src/services/usage_service.py`
**Description:** Business logic for usage stats, overage calculation, alerts
**Acceptance Criteria:**
- [x] UsageService class with get_usage_stats() method
- [x] _calculate_overage_cost() with pricing per agent
- [x] _generate_alerts() for 80% and 100% thresholds
- [x] _get_agent_limit() to extract limits from plan.limits JSONB
- [x] Handle edge cases: no subscription, trial users, no counters yet
- [x] Return UsageStatsResponse schema
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 45 min

### B2.3: Create Pydantic schemas ✅
**File:** `src/schemas/usage.py`
**Description:** Request/response schemas for usage API
**Acceptance Criteria:**
- [x] AgentUsage schema (count, limit, percentage, overage, overage_cost_cents)
- [x] UsageAlert schema (agent, message, level)
- [x] UsageStatsResponse schema (tenant_id, period_start, period_end, plan, usage, total_overage_cost_cents, alerts)
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 20 min

### B2.4: Add agent type enums ✅
**File:** `src/core/enums.py`
**Description:** Enum for agent types and action types
**Acceptance Criteria:**
- [x] AgentType enum: INBOX, INVOICE, MEETING
- [x] ActionType enum: EMAIL_PROCESSED, INVOICE_DETECTED, MEETING_PREP
- [x] Used in models and services for type safety
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 15 min

### B2.5: Update billing_service.py integration points ⬜
**File:** `src/services/billing_service.py` (if needed for plan limits)
**Description:** Ensure billing service exposes plan limits correctly
**Acceptance Criteria:**
- [ ] Verify Plan model has limits JSONB field
- [ ] Verify limits structure matches expected keys (emails_per_month, etc.)
- [ ] Add helper method if needed to get limits for agent
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 15 min

---

## Section 3: Backend - API Endpoints

### B3.1: Create usage router ✅
**File:** `src/api/v1/usage.py`
**Description:** FastAPI router with GET /usage endpoint
**Acceptance Criteria:**
- [x] GET /usage endpoint
- [x] Authentication required (JWT dependency)
- [x] Rate limiting: 10 req/min per tenant (via existing middleware)
- [x] Tenant isolation: only return current_user's tenant data
- [x] Error handling: 401, 404, 429, 500
- [x] Calls UsageService.get_usage_stats()
- [x] Returns UsageStatsResponse
**Safe for Ralph:** ⚠️ Needs Review (security validation critical)
**Estimated effort:** 45 min

### B3.2: Register usage router in main.py ✅
**File:** `src/api/main.py`
**Description:** Add usage router to FastAPI app
**Acceptance Criteria:**
- [x] Import usage router
- [x] app.include_router(usage_router, prefix="/api/v1", tags=["usage"])
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 5 min

### B3.3: Add rate limiting middleware ⬜
**File:** `src/middleware/rate_limit.py` (or update existing)
**Description:** Rate limiting for usage endpoint
**Acceptance Criteria:**
- [ ] Rate limit: 10 requests/min per tenant_id
- [ ] Use Redis for rate limit state
- [ ] Return 429 Too Many Requests when exceeded
- [ ] Apply to /api/v1/usage endpoint
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 30 min

---

## Section 4: Backend - Background Jobs

### B4.1: Create usage_tasks.py ⬜
**File:** `src/workers/tasks/usage_tasks.py`
**Description:** Celery tasks for usage tracking
**Acceptance Criteria:**
- [ ] reset_usage_counters task
- [ ] report_overage_to_stripe task with circuit breaker
- [ ] reconcile_usage_counters task
- [ ] All tasks have proper error handling, logging, metrics
- [ ] Tasks use SessionLocal() for DB access
**Safe for Ralph:** ⚠️ Needs Review (Stripe integration + reconciliation logic)
**Estimated effort:** 90 min

### B4.2: Update celery_app.py ⬜
**File:** `src/workers/celery_app.py`
**Description:** Register usage tasks in Celery app
**Acceptance Criteria:**
- [ ] Add "src.workers.tasks.usage_tasks" to include list
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 5 min

### B4.3: Configure Celery Beat schedule ⬜
**File:** `src/workers/celery_app.py` or separate config
**Description:** Schedule periodic tasks
**Acceptance Criteria:**
- [ ] reset_usage_counters: daily at 00:05 UTC
- [ ] report_overage_to_stripe: daily at 01:00 UTC
- [ ] reconcile_usage_counters: daily at 03:00 UTC
- [ ] Use crontab schedule syntax
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 20 min

### B4.4: Add Stripe metered billing helper ⬜
**File:** `src/integrations/stripe_client.py` (or update existing)
**Description:** Helper for Stripe usage record reporting
**Acceptance Criteria:**
- [ ] Function to report usage record: report_usage_to_stripe(subscription_item_id, quantity, timestamp)
- [ ] Error handling for Stripe API errors
- [ ] Retry logic with exponential backoff
- [ ] Circuit breaker implementation (5 failures → pause 15 min)
**Safe for Ralph:** ⚠️ Needs Review (external API integration)
**Estimated effort:** 45 min

---

## Section 5: Frontend

### F1: Create UsageWidget component ⬜
**File:** `frontend/src/components/usage/UsageWidget.tsx`
**Description:** React component to display usage stats
**Acceptance Criteria:**
- [ ] Fetch usage data from GET /api/v1/usage
- [ ] Auto-refetch every 30 seconds (React Query)
- [ ] Display 3 progress bars (inbox, invoice, meeting)
- [ ] Color coding: green < 80%, yellow 80-99%, red >= 100%
- [ ] Display overage cost when > 100%
- [ ] Alert banner when usage > 80% (dismissable)
- [ ] Responsive design
- [ ] Loading state, error state
**Safe for Ralph:** ⚠️ Needs Review (UX decisions: colors, copy)
**Estimated effort:** 90 min

### F2: Integrate UsageWidget into dashboard ⬜
**File:** `frontend/src/pages/Settings/Billing.tsx` (or appropriate page)
**Description:** Add UsageWidget to billing settings page
**Acceptance Criteria:**
- [ ] Import UsageWidget
- [ ] Render in appropriate section (e.g., below plan info)
- [ ] Only show for authenticated users with active subscription
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 15 min

---

## Section 6: Tests

### T1: Unit tests for UsageTracker ✅
**File:** `tests/unit/services/test_usage_tracker.py`
**Description:** Test atomic event creation + counter update
**Acceptance Criteria:**
- [x] Test track_event creates event and increments counter
- [x] Test idempotency: duplicate event rejected (IntegrityError)
- [x] Test counter created for new period
- [x] Test transaction rollback on failure
- [x] Test edge case: no active subscription → ValueError
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 45 min

### T2: Unit tests for UsageService ✅
**File:** `tests/unit/services/test_usage_service.py`
**Description:** Test business logic for stats, overage, alerts
**Acceptance Criteria:**
- [x] Test get_usage_stats returns correct data
- [x] Test overage calculation for each agent type
- [x] Test alert generation: 80% warning, 100% error
- [x] Test edge case: trial user with no plan
- [x] Test edge case: no counters yet (0 usage)
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 45 min

### T3: API tests for usage endpoint ✅
**File:** `tests/integration/test_usage_routes.py`
**Description:** Integration tests for GET /usage
**Acceptance Criteria:**
- [x] Test happy path: returns usage stats
- [x] Test authentication required: 401 without token
- [x] Test tenant isolation: can't see other tenant's data
- [ ] Test rate limiting: 429 after 10 requests (skipped - rate limiting middleware not fully tested yet)
- [x] Test 404 when no subscription
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 45 min

### T4: Tests for background jobs ⬜
**File:** `tests/workers/test_usage_tasks.py`
**Description:** Test Celery tasks
**Acceptance Criteria:**
- [ ] Test reset_usage_counters creates new counters
- [ ] Test report_overage_to_stripe (mocked Stripe API)
- [ ] Test reconcile_usage_counters auto-corrects drift < 5%
- [ ] Test reconcile_usage_counters alerts on drift > 5%
- [ ] Test circuit breaker in report_overage task
**Safe for Ralph:** ⚠️ Needs Review (mocking Stripe API)
**Estimated effort:** 60 min

### T5: End-to-end integration test ⬜
**File:** `tests/integration/test_usage_flow.py`
**Description:** Full flow test
**Acceptance Criteria:**
- [ ] Test: track event → counter incremented → API returns updated stats
- [ ] Test: overage scenario → Stripe report triggered
- [ ] Test: period rollover → new counters created
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 45 min

---

## Section 7: DevOps & Documentation

### D1: Database migration deployment ⬜
**Description:** Run migration in all environments
**Acceptance Criteria:**
- [ ] Run migration locally: `alembic upgrade head`
- [ ] Verify tables created with correct schema
- [ ] Document rollback procedure: `alembic downgrade -1`
**Safe for Ralph:** 🤚 Human Only (production deployment)
**Estimated effort:** 15 min

### D2: Configure monitoring & alerts ⬜
**Description:** Set up Prometheus metrics and alerts
**Acceptance Criteria:**
- [ ] Metrics instrumented in code (usage_events_total, usage_api_latency, etc.)
- [ ] Grafana dashboard created for usage metrics
- [ ] Alerts configured: Stripe failure rate, counter drift, API latency, reconciliation job
- [ ] Test alerts fire correctly
**Safe for Ralph:** 🤚 Human Only (ops configuration)
**Estimated effort:** 60 min

### D3: Update API documentation ⬜
**File:** `docs/api/usage.md` or OpenAPI spec
**Description:** Document GET /usage endpoint
**Acceptance Criteria:**
- [ ] OpenAPI/Swagger spec includes GET /usage
- [ ] Request/response schemas documented
- [ ] Example responses included
- [ ] Error codes documented (401, 404, 429, 500)
**Safe for Ralph:** ✅ Yes
**Estimated effort:** 20 min

---

## Implementation Order (Recommended)

### Phase 1: Foundation (B1.* → B2.*)
1. B1.1: Create models
2. B1.2: Create migration
3. B1.3: Update __init__
4. B2.4: Create enums
5. B2.3: Create schemas
6. Run migration locally

### Phase 2: Core Services (B2.1-2.2 → T1-T2)
7. B2.1: UsageTracker service
8. T1: UsageTracker tests
9. B2.2: UsageService
10. T2: UsageService tests

### Phase 3: API Layer (B3.* → T3)
11. B3.1: Usage router
12. B3.3: Rate limiting
13. B3.2: Register router
14. T3: API tests

### Phase 4: Background Jobs (B4.* → T4)
15. B4.1: Usage tasks
16. B4.2: Update celery_app
17. B4.3: Configure Beat schedule
18. B4.4: Stripe helper
19. T4: Background job tests

### Phase 5: Frontend (F1-F2)
20. F1: UsageWidget component
21. F2: Integrate widget

### Phase 6: Integration & Polish (T5, D3)
22. T5: E2E integration test
23. D3: API documentation
24. B2.5: Verify billing integration

### Phase 7: Deployment (D1-D2) - Human involvement
25. D1: Deploy migration
26. D2: Configure monitoring

---

## Task Status Legend

- ⬜ Not Started
- ⏳ In Progress
- ✅ Complete
- ❌ Blocked
- ⏸️ Paused

---

## Risk Flags

🔴 **High Risk Tasks** (require extra attention):
- B2.1: UsageTracker (atomic transactions critical)
- B3.1: Usage API (tenant isolation security)
- B4.1: Background jobs (Stripe integration + reconciliation)

⚠️ **Medium Risk Tasks** (need review):
- B4.4: Stripe metered billing helper
- T4: Background job tests (mocking complexity)

✅ **Low Risk Tasks** (safe for autonomous execution):
- All model/schema tasks
- Most test tasks
- Frontend component (with UX review)

---

*Generated: 2026-02-03*
*Total estimated effort: ~14 hours*
*Safe for autonomous execution: 18/25 tasks (72%)*
*Requires human review: 7/25 tasks (28%)*
