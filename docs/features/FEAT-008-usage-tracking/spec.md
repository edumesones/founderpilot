# FEAT-008: Usage Tracking

## Summary

Sistema de tracking de consumo en tiempo real para FounderPilot. Permite a los usuarios monitorear su uso de cada agente (InboxPilot, InvoicePilot, MeetingPilot) vs los límites de su plan, detectar y reportar overage a Stripe para facturación automática, y proporcionar métricas de uso para optimización del producto.

---

## User Stories

- [ ] Como **usuario activo** quiero **ver mi consumo actual de cada agente** para **saber cuánto he usado este mes**
- [ ] Como **usuario** quiero **ver qué porcentaje de mi límite mensual he consumido** para **saber si me acerco al límite**
- [ ] Como **usuario** quiero **recibir alertas cuando me acerque al límite de mi plan** para **decidir si upgrade o controlo mi uso**
- [ ] Como **usuario con overage** quiero **ver el cargo estimado de overage** para **saber cuánto pagaré de más este mes**
- [ ] Como **sistema** quiero **trackear cada acción de agente en tiempo real** para **tener datos precisos de consumo**
- [ ] Como **sistema** quiero **reportar overage a Stripe automáticamente** para **cobrar uso excesivo sin intervención manual**
- [ ] Como **admin** quiero **ver métricas agregadas de uso por tenant** para **entender patrones de consumo**

---

## Acceptance Criteria

- [ ] Cada acción de agente (email procesado, invoice creada, meeting preparado) se registra en DB
- [ ] Dashboard muestra consumo actual vs límite por agente en tiempo real
- [ ] Barra de progreso visual (0-100%) para cada agente
- [ ] Alerta cuando consumo > 80% del límite
- [ ] Cálculo automático de overage cuando consumo > límite
- [ ] Reporte de overage a Stripe via metered billing API
- [ ] Reset de contador al inicio del nuevo período de facturación
- [ ] API endpoint para obtener usage stats por tenant
- [ ] Audit log de todas las acciones trackeadas
- [ ] Tests unitarios para cálculo de overage

---

## Technical Decisions

| # | Área | Pregunta | Decisión | Notas |
|---|------|----------|----------|-------|
| 1 | Storage | ¿Dónde guardar usage events? | **PostgreSQL table `usage_events`** | Relacional para joins con subscriptions |
| 2 | Granularity | ¿Qué trackear exactamente? | **Cada acción facturable** | Email procesado, invoice detectada, meeting prep completado |
| 3 | Aggregation | ¿Pre-calcular o calcular on-demand? | **Híbrido: events + cached counters** | Events para audit, counter cache para performance |
| 4 | Reset | ¿Cómo resetear contadores? | **Background job al cambio de período** | Cronjob diario verifica subscription.current_period_start |
| 5 | Overage Reporting | ¿Cuándo reportar a Stripe? | **Batch diario + al cierre de período** | Report accumulated usage to Stripe metered billing |
| 6 | Real-time | ¿Actualizar UI en tiempo real? | **No - polling cada 30s en dashboard** | Evita complejidad de WebSockets por ahora |
| 7 | Limits Enforcement | ¿Bloquear cuando excede límite? | **No - permitir overage y cobrar** | Business model: no friction, monetize overage |
| 8 | Alerts | ¿Cómo notificar al usuario? | **In-app banner + Slack message** | Email para v1.1 |
| 9 | Metrics | ¿Qué métricas exponer a admin? | **Ver sección Observability** | Prometheus metrics + dashboard interno |
| 10 | Data Retention | ¿Cuánto tiempo guardar events? | **90 días** | Suficiente para disputes, luego archive/delete |

---

## Scope

### ✅ In Scope (MVP)

- Modelo `UsageEvent` para registrar cada acción
- Modelo `UsageCounter` para cache agregado por tenant/agente/período
- Servicio `UsageTracker` para registrar eventos
- API endpoint `GET /api/v1/usage` para dashboard
- UI component `UsageWidget` mostrando barras de progreso
- Alert cuando consumo > 80%
- Cálculo de overage cost
- Background job para reset mensual
- Background job para reportar overage a Stripe
- Tests para lógica de overage
- Audit logging de eventos de usage

### ❌ Out of Scope

- Real-time WebSocket updates (v1.1)
- Email notifications (v1.1 - solo in-app y Slack por ahora)
- Usage analytics dashboard para admins (v1.1)
- Historical usage graphs (v1.1)
- Export usage data (v1.1)
- Custom usage alerts por usuario (v1.1)
- Predictive "days until limit" (v1.1)

---

## Dependencies

### Requires (this feature needs)
- [x] FEAT-002 - Billing & Plans (plan limits, subscription periods)
- [x] FEAT-001 - Auth & Onboarding (tenant_id)
- [x] PostgreSQL database
- [x] Background job system (Celery/ARQ)
- [x] Stripe account con metered billing configurado

### Blocks (features that need this)
- Ninguna feature bloqueada - esto es enhancement post-billing

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Usuario en trial sin plan_id | Usar trial limits generosos (no strict limit) |
| Subscription sin plan (edge case) | Return 0 usage, log warning |
| Stripe API falla al reportar overage | Retry 3 veces con backoff, log error, continuar (reportar en siguiente batch) |
| Usuario cambia de plan mid-period | Proratear límites? **NO - usar límites del nuevo plan completo** |
| Background job falla | Logs + alertas + retry automático |
| Contador desincronizado con events | Job de reconciliación diario (compare sum(events) vs counter) |
| Múltiples workers escribiendo events | Use DB transactions + increment atomically |

---

## UI/UX Decisions

| Elemento | Decisión | Referencia |
|----------|----------|------------|
| Layout | Dashboard `/settings/billing` section | Same page as plan info |
| Visual | Progress bars (green → yellow@80% → red@100%) | Material UI Linear Progress |
| Alerts | Banner at top when > 80% | Dismissable but shows again next session if still > 80% |
| Overage Display | Show estimated overage cost: "Est. overage: $2.40" | Below progress bar when > 100% |
| Refresh | Auto-refresh every 30s when on page | Use SWR or React Query |
| Empty State | "No usage this period yet" | Friendly illustration |

---

## Security Considerations

- [x] ¿Requiere autenticación? **YES - usuario autenticado only**
- [x] ¿Qué datos son sensibles? **Usage stats son sensibles - solo owner del tenant puede ver**
- [x] ¿Necesita rate limiting? **YES - endpoint /api/v1/usage limitado a 10 req/min por tenant**
- [x] ¿Cumple con GDPR/privacidad? **YES - usage events vinculados a tenant_id, no PII directamente**

### Security Controls
- API endpoint valida que `current_user.tenant_id == requested_tenant_id`
- No exponer usage de otros tenants
- Rate limit en endpoint de usage
- Logs de acceso a usage stats (audit trail)

---

## Data Model

### UsageEvent
```python
class UsageEvent(Base):
    """Individual usage event - audit trail"""
    __tablename__ = "usage_events"

    id = UUID (primary key)
    tenant_id = UUID (FK to tenants)
    agent = String  # "inbox", "invoice", "meeting"
    action_type = String  # "email_processed", "invoice_detected", "meeting_prep"
    resource_id = UUID (nullable)  # FK to email_record, invoice, meeting
    quantity = Integer (default=1)  # Usually 1, but allows for batch actions
    metadata = JSONB (nullable)  # Extra context
    created_at = DateTime
```

### UsageCounter
```python
class UsageCounter(Base):
    """Aggregated usage counter - performance cache"""
    __tablename__ = "usage_counters"

    id = UUID (primary key)
    tenant_id = UUID (FK to tenants, unique constraint with period_start/agent)
    agent = String  # "inbox", "invoice", "meeting"
    period_start = DateTime  # subscription.current_period_start
    period_end = DateTime  # subscription.current_period_end
    count = Integer (default=0)
    last_event_at = DateTime (nullable)
    updated_at = DateTime (onupdate)

    # Unique constraint: (tenant_id, agent, period_start)
```

---

## API Design

### GET /api/v1/usage
**Auth:** Required (JWT)
**Returns:** Current period usage for authenticated user's tenant

**Response:**
```json
{
  "tenant_id": "uuid",
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-02-01T00:00:00Z",
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
      "message": "You've used 85% of your email quota",
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

---

## Overage Pricing

From `docs/project.md`:
- **Email:** $0.02/email extra
- **Invoice:** $0.10/invoice extra
- **Meeting:** $0.15/meeting extra

---

## Background Jobs

### 1. Reset Monthly Counters
**Trigger:** Daily cron (check if period rolled over)
**Logic:**
```python
for subscription in active_subscriptions:
    if subscription.current_period_start > last_counter.period_start:
        create_new_counter_for_new_period()
```

### 2. Report Overage to Stripe
**Trigger:** Daily batch + end of period
**Logic:**
```python
for counter in counters_with_overage:
    overage = counter.count - limit
    stripe.SubscriptionItem.create_usage_record(
        subscription_item_id,
        quantity=overage,
        timestamp=int(time.time()),
        action='set'
    )
```

### 3. Usage Reconciliation
**Trigger:** Daily at 3am
**Logic:** Compare `sum(usage_events.quantity)` vs `usage_counter.count` and log discrepancies

---

## Observability

### Metrics (Prometheus)
- `usage_events_total{tenant_id, agent, action_type}` - Counter
- `usage_counter_value{tenant_id, agent}` - Gauge
- `usage_overage_cost_cents{tenant_id}` - Gauge
- `usage_api_requests_total{status}` - Counter
- `stripe_usage_report_total{status}` - Counter (success/failure)

### Logs
- Every usage event recorded: `INFO: UsageEvent created: tenant={}, agent={}, action={}`
- Overage detected: `WARNING: Overage detected: tenant={}, agent={}, overage={}`
- Stripe report success: `INFO: Reported overage to Stripe: tenant={}, amount={}`
- Stripe report failure: `ERROR: Failed to report overage to Stripe: tenant={}, error={}`

### Alerts
- Stripe API failure rate > 5% → Page on-call
- Usage counter reconciliation errors > 10/day → Slack alert

---

## Open Questions

- [x] ¿Cómo manejar trial users? → Usar límites generosos, no strict enforcement
- [x] ¿Qué pasa si usuario downgrade mid-period? → Usar límites del nuevo plan, no proratear
- [ ] ¿Mostrar histórico de períodos anteriores? → Out of scope v1, v1.1 feature
- [ ] ¿Permitir usuario configurar alertas personalizadas? → Out of scope v1, v1.1 feature

---

## Interview Log

### Session 1 - 2026-02-03
- **Discutido:**
  - Revisado billing model existente (FEAT-002)
  - Definido scope de usage tracking MVP
  - Decidido arquitectura: events + counter cache
  - Definido overage handling: report to Stripe metered billing

- **Decisiones:**
  - Hybrid storage: events (audit) + counters (performance)
  - No blocking on limit - allow overage and charge
  - In-app alerts + Slack (no email for v1)
  - Polling-based UI refresh (no WebSockets for v1)

- **Pendiente:**
  - Think Critically analysis
  - Technical design in design.md

---

*Status: ✅ Interview Complete*
*Created: 2026-02-03*
*Last updated: 2026-02-03*
