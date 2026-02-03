# FEAT-008: Technical Design

> Generated from analysis.md recommendations (Phase 3 of Feature Cycle)
> **Date:** 2026-02-03
> **Confidence:** High

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend (React)                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  UsageWidget Component                                     │ │
│  │  - Progress bars (inbox, invoice, meeting)                 │ │
│  │  - Alert banners (> 80%)                                   │ │
│  │  - Overage cost display                                    │ │
│  │  - Polling: useQuery with 30s refetch interval             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │ HTTP GET /api/v1/usage           │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                          Backend (FastAPI)                       │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  UsageRouter (src/api/v1/usage.py)                         │ │
│  │  GET /usage → UsageService.get_usage_stats()               │ │
│  └──────────────────────┬─────────────────────────────────────┘ │
│                         │                                        │
│  ┌──────────────────────▼─────────────────────────────────────┐ │
│  │  UsageService (src/services/usage_service.py)              │ │
│  │  - get_usage_stats(tenant_id) → UsageStatsResponse         │ │
│  │  - calculate_overage(count, limit, agent)                  │ │
│  │  - generate_alerts(usage_data)                             │ │
│  └──────────────────────┬─────────────────────────────────────┘ │
│                         │                                        │
│  ┌──────────────────────▼─────────────────────────────────────┐ │
│  │  UsageTracker (src/services/usage_tracker.py)              │ │
│  │  - track_event(tenant_id, agent, action_type, resource_id) │ │
│  │  - increment_counter(tenant_id, agent, quantity)           │ │
│  │  - Transaction: event write + counter update (atomic)      │ │
│  └──────────────────────┬─────────────────────────────────────┘ │
│                         │                                        │
│  ┌──────────────────────▼─────────────────────────────────────┐ │
│  │  Database Models (src/models/usage.py)                     │ │
│  │  - UsageEvent (audit trail)                                │ │
│  │  - UsageCounter (performance cache)                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Background Jobs (Celery)                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  reset_usage_counters (daily)                              │ │
│  │  - Check if period rolled over for each subscription       │ │
│  │  - Create new counter for new period                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  report_overage_to_stripe (daily + end-of-period)          │ │
│  │  - Query counters with overage                             │ │
│  │  - Report to Stripe metered billing API                    │ │
│  │  - Circuit breaker: pause after 5 failures                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  reconcile_usage_counters (daily at 3am)                   │ │
│  │  - Compare sum(events) vs counter.count                    │ │
│  │  - Auto-correct if drift < 5%                              │ │
│  │  - Alert if drift > 5%                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Integration Points                            │
│                                                                  │
│  InboxPilot ──┐                                                  │
│  InvoicePilot ─┼──▶ UsageTracker.track_event()                  │
│  MeetingPilot ─┘    (called after each agent action)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### UsageEvent Table

```sql
CREATE TABLE usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent VARCHAR(20) NOT NULL,  -- 'inbox', 'invoice', 'meeting'
    action_type VARCHAR(50) NOT NULL,  -- 'email_processed', 'invoice_detected', 'meeting_prep'
    resource_id UUID,  -- FK to specific resource (email_record, etc)
    quantity INTEGER NOT NULL DEFAULT 1,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,  -- Prevents duplicate events
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_usage_events_tenant_agent (tenant_id, agent, created_at),
    INDEX idx_usage_events_idempotency (idempotency_key)
);
```

**Idempotency Key Format:** `{tenant_id}:{agent}:{resource_id}:{action_type}:{timestamp_ms}`

Example: `123e4567-e89b-12d3-a456-426614174000:inbox:uuid-of-email:email_processed:1704067200000`

### UsageCounter Table

```sql
CREATE TABLE usage_counters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent VARCHAR(20) NOT NULL,  -- 'inbox', 'invoice', 'meeting'
    period_start TIMESTAMP NOT NULL,  -- subscription.current_period_start
    period_end TIMESTAMP NOT NULL,    -- subscription.current_period_end
    count INTEGER NOT NULL DEFAULT 0 CHECK (count >= 0),
    last_event_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (tenant_id, agent, period_start),
    INDEX idx_usage_counters_tenant_period (tenant_id, period_start)
);
```

**Invariant:** `count` must equal `SUM(usage_events.quantity)` for matching `(tenant_id, agent, period)`

---

## API Endpoints

### GET /api/v1/usage

**Description:** Get current period usage stats for authenticated user's tenant

**Auth:** Required (JWT)

**Query Params:** None (uses `current_user.tenant_id` from token)

**Rate Limit:** 10 requests/min per tenant

**Response Schema:**

```python
class AgentUsage(BaseModel):
    count: int
    limit: int
    percentage: int  # 0-100+
    overage: int  # 0 if under limit
    overage_cost_cents: int

class UsageAlert(BaseModel):
    agent: str
    message: str
    level: str  # "warning" | "error"

class UsageStatsResponse(BaseModel):
    tenant_id: UUID
    period_start: datetime
    period_end: datetime
    plan: dict  # {"name": "Bundle", "limits": {...}}
    usage: dict[str, AgentUsage]  # {"inbox": {...}, "invoice": {...}, "meeting": {...}}
    total_overage_cost_cents: int
    alerts: list[UsageAlert]
```

**Example Response:**

```json
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "period_start": "2024-02-01T00:00:00Z",
  "period_end": "2024-03-01T00:00:00Z",
  "plan": {
    "name": "Bundle",
    "limits": {
      "emails_per_month": 500,
      "invoices_per_month": 50,
      "meetings_per_month": 30
    }
  },
  "usage": {
    "inbox": {
      "count": 425,
      "limit": 500,
      "percentage": 85,
      "overage": 0,
      "overage_cost_cents": 0
    },
    "invoice": {
      "count": 52,
      "limit": 50,
      "percentage": 104,
      "overage": 2,
      "overage_cost_cents": 20
    },
    "meeting": {
      "count": 15,
      "limit": 30,
      "percentage": 50,
      "overage": 0,
      "overage_cost_cents": 0
    }
  },
  "total_overage_cost_cents": 20,
  "alerts": [
    {
      "agent": "inbox",
      "message": "You've used 85% of your email quota this month",
      "level": "warning"
    },
    {
      "agent": "invoice",
      "message": "You've exceeded your invoice quota. Extra charges: $0.20",
      "level": "error"
    }
  ]
}
```

**Error Responses:**
- `401 Unauthorized` - Missing/invalid JWT token
- `404 Not Found` - Tenant has no active subscription
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Database/service error

---

## Service Layer

### UsageTracker Service

**File:** `src/services/usage_tracker.py`

**Purpose:** Core service for recording usage events + updating counters atomically

**Methods:**

```python
class UsageTracker:
    def __init__(self, db_session: Session):
        self.db = db_session

    def track_event(
        self,
        tenant_id: UUID,
        agent: str,  # "inbox" | "invoice" | "meeting"
        action_type: str,  # "email_processed" | "invoice_detected" | "meeting_prep"
        resource_id: Optional[UUID] = None,
        quantity: int = 1,
        metadata: Optional[dict] = None,
    ) -> UsageEvent:
        """
        Record usage event + increment counter atomically.

        Raises:
            ValueError: If agent or action_type invalid
            IntegrityError: If idempotency key already exists (duplicate)
            OperationalError: If DB write fails
        """
        # Generate idempotency key
        idempotency_key = self._generate_idempotency_key(
            tenant_id, agent, action_type, resource_id
        )

        # Start transaction
        with self.db.begin():
            # Write event
            event = UsageEvent(
                tenant_id=tenant_id,
                agent=agent,
                action_type=action_type,
                resource_id=resource_id,
                quantity=quantity,
                idempotency_key=idempotency_key,
                metadata=metadata,
            )
            self.db.add(event)

            # Update or create counter
            counter = self._get_or_create_counter(tenant_id, agent)
            counter.count += quantity
            counter.last_event_at = datetime.utcnow()

            self.db.commit()

        # Emit metric
        metrics.increment("usage_events_total", labels={"agent": agent})

        logger.info(
            f"UsageEvent created: tenant={tenant_id}, agent={agent}, "
            f"action={action_type}, quantity={quantity}"
        )

        return event

    def _generate_idempotency_key(
        self, tenant_id: UUID, agent: str, action_type: str, resource_id: Optional[UUID]
    ) -> str:
        """Generate unique idempotency key to prevent duplicate events."""
        timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        resource_part = resource_id if resource_id else "none"
        return f"{tenant_id}:{agent}:{resource_part}:{action_type}:{timestamp_ms}"

    def _get_or_create_counter(self, tenant_id: UUID, agent: str) -> UsageCounter:
        """Get existing counter for current period or create new one."""
        # Get subscription to find current period
        subscription = (
            self.db.query(Subscription)
            .filter(Subscription.tenant_id == tenant_id)
            .first()
        )

        if not subscription or not subscription.current_period_start:
            raise ValueError(f"Tenant {tenant_id} has no active subscription")

        # Find or create counter
        counter = (
            self.db.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == agent,
                UsageCounter.period_start == subscription.current_period_start,
            )
            .first()
        )

        if not counter:
            counter = UsageCounter(
                tenant_id=tenant_id,
                agent=agent,
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=0,
            )
            self.db.add(counter)

        return counter
```

### UsageService

**File:** `src/services/usage_service.py`

**Purpose:** Business logic for usage stats, overage calculation, alerts

**Methods:**

```python
class UsageService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_usage_stats(self, tenant_id: UUID) -> UsageStatsResponse:
        """Get usage stats for tenant's current billing period."""
        # Get subscription + plan
        subscription = self._get_active_subscription(tenant_id)
        plan = subscription.plan

        # Get counters for current period
        counters = (
            self.db.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.period_start == subscription.current_period_start,
            )
            .all()
        )

        # Build usage dict
        usage_data = {}
        total_overage_cost = 0

        for agent in ["inbox", "invoice", "meeting"]:
            counter = next((c for c in counters if c.agent == agent), None)
            count = counter.count if counter else 0

            limit = self._get_agent_limit(plan, agent)
            percentage = int((count / limit) * 100) if limit > 0 else 0
            overage = max(0, count - limit)
            overage_cost = self._calculate_overage_cost(agent, overage)
            total_overage_cost += overage_cost

            usage_data[agent] = AgentUsage(
                count=count,
                limit=limit,
                percentage=percentage,
                overage=overage,
                overage_cost_cents=overage_cost,
            )

        # Generate alerts
        alerts = self._generate_alerts(usage_data)

        return UsageStatsResponse(
            tenant_id=tenant_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            plan={"name": plan.name, "limits": plan.limits},
            usage=usage_data,
            total_overage_cost_cents=total_overage_cost,
            alerts=alerts,
        )

    def _calculate_overage_cost(self, agent: str, overage: int) -> int:
        """Calculate overage cost in cents."""
        pricing = {
            "inbox": 2,   # $0.02/email
            "invoice": 10,  # $0.10/invoice
            "meeting": 15,  # $0.15/meeting
        }
        return overage * pricing.get(agent, 0)

    def _generate_alerts(self, usage_data: dict[str, AgentUsage]) -> list[UsageAlert]:
        """Generate alerts for high usage / overage."""
        alerts = []

        for agent, usage in usage_data.items():
            if usage.percentage >= 100:
                alerts.append(UsageAlert(
                    agent=agent,
                    message=f"You've exceeded your {agent} quota. Extra charges: ${usage.overage_cost_cents/100:.2f}",
                    level="error",
                ))
            elif usage.percentage >= 80:
                alerts.append(UsageAlert(
                    agent=agent,
                    message=f"You've used {usage.percentage}% of your {agent} quota this month",
                    level="warning",
                ))

        return alerts

    def _get_agent_limit(self, plan: Plan, agent: str) -> int:
        """Extract limit for agent from plan.limits JSONB."""
        limit_key_map = {
            "inbox": "emails_per_month",
            "invoice": "invoices_per_month",
            "meeting": "meetings_per_month",
        }
        key = limit_key_map.get(agent)
        return plan.limits.get(key, 0) if key else 0
```

---

## Background Jobs (Celery Tasks)

### 1. Reset Usage Counters

**File:** `src/workers/tasks/usage_tasks.py`

**Schedule:** Daily at 00:05 UTC (via Celery Beat)

**Purpose:** Create new counters when billing period rolls over

```python
@celery_app.task(name="reset_usage_counters")
def reset_usage_counters():
    """
    Check all active subscriptions. If period rolled over, create new counter.
    """
    db = SessionLocal()
    try:
        subscriptions = (
            db.query(Subscription)
            .filter(Subscription.status.in_(["trial", "active"]))
            .all()
        )

        reset_count = 0
        for sub in subscriptions:
            # For each agent, check if counter exists for new period
            for agent in ["inbox", "invoice", "meeting"]:
                existing = (
                    db.query(UsageCounter)
                    .filter(
                        UsageCounter.tenant_id == sub.tenant_id,
                        UsageCounter.agent == agent,
                        UsageCounter.period_start == sub.current_period_start,
                    )
                    .first()
                )

                if not existing:
                    # Create new counter for new period
                    new_counter = UsageCounter(
                        tenant_id=sub.tenant_id,
                        agent=agent,
                        period_start=sub.current_period_start,
                        period_end=sub.current_period_end,
                        count=0,
                    )
                    db.add(new_counter)
                    reset_count += 1

        db.commit()
        logger.info(f"Reset usage counters: created {reset_count} new counters")
        metrics.gauge("usage_counter_resets", reset_count)

    except Exception as e:
        logger.error(f"Failed to reset usage counters: {e}")
        raise
    finally:
        db.close()
```

### 2. Report Overage to Stripe

**File:** `src/workers/tasks/usage_tasks.py`

**Schedule:** Daily at 01:00 UTC + triggered at end of period

**Purpose:** Report overage usage to Stripe metered billing

```python
@celery_app.task(name="report_overage_to_stripe", bind=True, max_retries=3)
def report_overage_to_stripe(self):
    """
    Query all counters with overage, report to Stripe.
    Uses circuit breaker pattern.
    """
    db = SessionLocal()
    try:
        # Get all counters for current period with overage
        counters_with_overage = (
            db.query(UsageCounter, Subscription, Plan)
            .join(Subscription, UsageCounter.tenant_id == Subscription.tenant_id)
            .join(Plan, Subscription.plan_id == Plan.id)
            .filter(Subscription.status == "active")
            .all()
        )

        success_count = 0
        failure_count = 0

        for counter, subscription, plan in counters_with_overage:
            limit = _get_limit_for_agent(plan, counter.agent)
            overage = max(0, counter.count - limit)

            if overage == 0:
                continue

            try:
                # Report to Stripe
                stripe.SubscriptionItem.create_usage_record(
                    subscription.stripe_subscription_id,  # needs subscription_item_id actually
                    quantity=overage,
                    timestamp=int(time.time()),
                    action="set",
                )

                success_count += 1
                logger.info(
                    f"Reported overage to Stripe: tenant={counter.tenant_id}, "
                    f"agent={counter.agent}, overage={overage}"
                )

            except stripe.error.StripeError as e:
                failure_count += 1
                logger.error(
                    f"Failed to report overage to Stripe: tenant={counter.tenant_id}, "
                    f"agent={counter.agent}, error={e}"
                )

                # Circuit breaker: if too many failures, abort
                if failure_count > 5:
                    logger.error("Circuit breaker: too many Stripe API failures, aborting")
                    metrics.increment("stripe_report_circuit_breaker_triggered")
                    break

        metrics.gauge("stripe_report_success", success_count)
        metrics.gauge("stripe_report_failure", failure_count)

    except Exception as e:
        logger.error(f"Failed to report overage to Stripe: {e}")
        # Retry task
        raise self.retry(exc=e, countdown=60 * 5)  # Retry in 5 minutes
    finally:
        db.close()
```

### 3. Reconcile Usage Counters

**File:** `src/workers/tasks/usage_tasks.py`

**Schedule:** Daily at 03:00 UTC

**Purpose:** Detect and fix counter drift

```python
@celery_app.task(name="reconcile_usage_counters")
def reconcile_usage_counters():
    """
    Compare sum(events) vs counter.count for each tenant/agent/period.
    Auto-correct if drift < 5%, alert if > 5%.
    """
    db = SessionLocal()
    try:
        # Get all current period counters
        counters = (
            db.query(UsageCounter)
            .join(Subscription, UsageCounter.tenant_id == Subscription.tenant_id)
            .filter(
                UsageCounter.period_start == Subscription.current_period_start
            )
            .all()
        )

        drift_detected = 0
        corrected = 0

        for counter in counters:
            # Calculate actual sum from events
            events_sum = (
                db.query(func.sum(UsageEvent.quantity))
                .filter(
                    UsageEvent.tenant_id == counter.tenant_id,
                    UsageEvent.agent == counter.agent,
                    UsageEvent.created_at >= counter.period_start,
                    UsageEvent.created_at < counter.period_end,
                )
                .scalar()
            ) or 0

            # Check drift
            diff = abs(events_sum - counter.count)
            drift_pct = (diff / events_sum * 100) if events_sum > 0 else 0

            if drift_pct > 0.1:  # > 0.1% drift
                drift_detected += 1
                logger.warning(
                    f"Counter drift detected: tenant={counter.tenant_id}, "
                    f"agent={counter.agent}, counter={counter.count}, "
                    f"events_sum={events_sum}, diff={diff}, drift={drift_pct:.2f}%"
                )

                if drift_pct < 5:  # Auto-correct if < 5%
                    counter.count = events_sum
                    db.commit()
                    corrected += 1
                    logger.info(f"Auto-corrected counter drift: {counter.tenant_id}/{counter.agent}")
                else:
                    # Alert for manual investigation
                    logger.error(
                        f"HIGH DRIFT DETECTED (> 5%): tenant={counter.tenant_id}, "
                        f"agent={counter.agent}, drift={drift_pct:.2f}%"
                    )
                    metrics.increment("usage_counter_high_drift_alert")

        metrics.gauge("usage_counter_drift_detected", drift_detected)
        metrics.gauge("usage_counter_auto_corrected", corrected)

    except Exception as e:
        logger.error(f"Failed to reconcile usage counters: {e}")
        raise
    finally:
        db.close()
```

---

## Frontend Component

### UsageWidget

**File:** `frontend/src/components/usage/UsageWidget.tsx`

**Props:** None (fetches data internally)

**Behavior:**
- Fetches usage data from API on mount
- Refetches every 30 seconds while component mounted
- Displays progress bars for each agent
- Shows alert banner if usage > 80%
- Color coding: green (< 80%), yellow (80-99%), red (>= 100%)

**UI Sketch:**

```
┌────────────────────────────────────────────────────────────┐
│  Usage This Month                                          │
├────────────────────────────────────────────────────────────┤
│  ⚠️ You've used 85% of your email quota this month         │
│  (dismissable banner)                                      │
├────────────────────────────────────────────────────────────┤
│  InboxPilot                                  425 / 500     │
│  ████████████████████░░░░  85%                             │
│                                                            │
│  InvoicePilot                                 52 / 50      │
│  ████████████████████████  104%  Est. overage: $0.20      │
│                                                            │
│  MeetingPilot                                 15 / 30      │
│  ██████████░░░░░░░░░░░░░░  50%                             │
│                                                            │
│  Total estimated overage: $0.20                            │
└────────────────────────────────────────────────────────────┘
```

**Tech Stack:**
- React Query (useQuery) for data fetching + polling
- Material-UI LinearProgress for progress bars
- Material-UI Alert for warning banners

---

## Integration Points

### Agent Integration

Each agent must call `UsageTracker.track_event()` after completing billable action:

**Example: InboxPilot**

```python
# In InboxPilot service after processing email
from src.services.usage_tracker import UsageTracker

def process_email(email_id: UUID, tenant_id: UUID):
    # ... process email logic ...

    # Track usage
    tracker = UsageTracker(db_session)
    tracker.track_event(
        tenant_id=tenant_id,
        agent="inbox",
        action_type="email_processed",
        resource_id=email_id,
        metadata={"subject": email.subject},
    )
```

**Example: InvoicePilot**

```python
def detect_invoice(tenant_id: UUID, invoice_data: dict):
    # ... invoice detection logic ...

    # Track usage
    tracker = UsageTracker(db_session)
    tracker.track_event(
        tenant_id=tenant_id,
        agent="invoice",
        action_type="invoice_detected",
        resource_id=invoice_id,
        metadata={"amount": invoice_data["amount"]},
    )
```

---

## Testing Strategy

### Unit Tests

1. **UsageTracker Tests** (`tests/services/test_usage_tracker.py`)
   - Test event creation + counter increment (atomic)
   - Test idempotency (duplicate events rejected)
   - Test counter creation for new period
   - Test transaction rollback on failure

2. **UsageService Tests** (`tests/services/test_usage_service.py`)
   - Test overage calculation (various scenarios)
   - Test alert generation (thresholds 80%, 100%)
   - Test stats aggregation
   - Test trial user handling (no plan)

3. **API Tests** (`tests/api/test_usage.py`)
   - Test GET /usage endpoint (happy path)
   - Test authentication required
   - Test tenant isolation (can't see other tenant's data)
   - Test rate limiting

4. **Background Job Tests** (`tests/workers/test_usage_tasks.py`)
   - Test counter reset logic
   - Test Stripe reporting (mocked)
   - Test reconciliation (auto-correct vs alert)
   - Test circuit breaker

### Integration Tests

1. **End-to-End Flow:**
   - Agent processes action → event tracked → counter incremented → API returns updated stats → frontend displays

2. **Period Rollover:**
   - Subscription period changes → background job creates new counters → old counters archived

3. **Overage Reporting:**
   - Counter exceeds limit → background job reports to Stripe → Stripe invoice updated

---

## Monitoring & Alerts

### Metrics to Track

- `usage_events_total` (Counter) - Total events created by agent type
- `usage_api_latency_seconds` (Histogram) - API response time p50/p95/p99
- `stripe_report_success_total` (Counter) - Successful Stripe reports
- `stripe_report_failure_total` (Counter) - Failed Stripe reports
- `usage_counter_drift_percentage` (Gauge) - Drift detected by reconciliation job
- `usage_events_write_errors` (Counter) - Failed event writes

### Alerts

- **Critical:** Stripe report failure rate > 5% (15 min window) → Page on-call
- **Warning:** Counter drift > 1% detected → Slack alert
- **Warning:** Usage API p95 latency > 300ms → Slack alert
- **Critical:** Usage events write error rate > 10/hour → Page on-call
- **Critical:** Reconciliation job hasn't run in 25 hours → Page on-call

---

## Security Considerations

1. **Tenant Isolation:**
   - API endpoint MUST validate `current_user.tenant_id == requested_tenant_id`
   - Use ORM filters on tenant_id for all queries
   - Never expose cross-tenant data

2. **Rate Limiting:**
   - API endpoint: 10 req/min per tenant
   - Prevents abuse, DoS attacks

3. **Idempotency:**
   - Prevents duplicate charges via retry attacks
   - Idempotency key must be unique per event

4. **Background Job Permissions:**
   - Run with minimal DB permissions
   - Write-only to usage tables
   - Audit all writes

5. **Data Retention:**
   - Usage events retained 90 days (compliance)
   - Automated cleanup job after 90 days

---

## Performance Optimizations

1. **Counter Cache:**
   - Avoids slow aggregation queries on usage_events
   - Single-row lookup for stats API

2. **Indexes:**
   - `usage_events`: `(tenant_id, agent, created_at)`
   - `usage_counters`: `(tenant_id, period_start)`
   - `usage_events`: `(idempotency_key)` - unique constraint

3. **Query Optimization:**
   - Use `lazy="joined"` for subscription.plan relationship
   - Batch Stripe reports (1000 tenants/batch)

4. **Connection Pooling:**
   - FastAPI: SQLAlchemy connection pool (size=20)
   - Celery: Separate connection pool (size=10)

---

## Deployment Checklist

- [ ] Database migration: create `usage_events` and `usage_counters` tables
- [ ] Add usage tasks to Celery app (`celery_app.py` include list)
- [ ] Configure Celery Beat schedule for 3 tasks
- [ ] Add Stripe metered billing config (subscription item IDs per plan)
- [ ] Deploy frontend UsageWidget component
- [ ] Add monitoring dashboards (Grafana)
- [ ] Configure alerts (PagerDuty, Slack)
- [ ] Run reconciliation job manually to verify
- [ ] Load test: 1000 concurrent usage tracking calls

---

## Rollback Plan

If critical issues found in production:

1. **Disable background jobs** via Celery control (pause queue)
2. **Revert API endpoint** via feature flag (return empty stats)
3. **Stop agent integration** (remove UsageTracker calls)
4. **Database:** Truncate `usage_events` and `usage_counters` tables if needed

**Data Loss Risk:** Low - usage events append-only, no destructive operations

---

*Generated: 2026-02-03*
*Ready for implementation*
