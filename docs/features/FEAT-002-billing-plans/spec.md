# FEAT-002: Billing & Plans

## Summary

Sistema de facturación y planes para FounderPilot. Integración con Stripe para subscripciones mensuales, gestión de planes por agente (InboxPilot, InvoicePilot, MeetingPilot) o bundle, período de prueba de 14 días, y sistema de overage para uso excesivo. Permite a los usuarios elegir su plan, gestionar su suscripción y ver el estado de facturación.

---

## User Stories

- [x] Como **nuevo usuario** quiero **tener 14 días de prueba gratuita con acceso a todos los agentes** para **evaluar el producto antes de pagar**
- [x] Como **usuario en trial** quiero **ver cuántos días me quedan de prueba** para **saber cuándo debo decidir**
- [x] Como **usuario** quiero **elegir entre planes individuales por agente o el bundle** para **pagar solo por lo que necesito**
- [x] Como **usuario** quiero **pagar con tarjeta de crédito via Stripe** para **una experiencia de pago segura y familiar**
- [x] Como **usuario** quiero **ver mi consumo actual vs límites de mi plan** para **saber si me acerco al límite**
- [x] Como **usuario** quiero **poder cambiar de plan (upgrade/downgrade)** para **ajustar según mis necesidades**
- [x] Como **usuario** quiero **poder cancelar mi suscripción** para **dejar de pagar si ya no uso el servicio**
- [x] Como **sistema** quiero **cobrar overage automáticamente** para **monetizar uso excesivo sin fricción**

---

## Acceptance Criteria

- [x] Usuario nuevo entra automáticamente en trial de 14 días
- [x] Trial incluye acceso a los 3 agentes con límites generosos
- [x] UI muestra días restantes de trial y CTA para suscribirse
- [x] 4 planes disponibles: InboxPilot ($29), InvoicePilot ($19), MeetingPilot ($19), Bundle ($49)
- [x] Checkout via Stripe Checkout (hosted page)
- [x] Webhook de Stripe actualiza estado de suscripción en DB
- [x] Portal de Stripe para gestión de método de pago y facturas
- [x] Upgrade/downgrade prorrateado automáticamente por Stripe
- [x] Cancelación efectiva al final del período de facturación
- [x] Overage calculado y cobrado mensualmente
- [x] Dashboard de billing muestra: plan actual, próximo cobro, consumo, facturas

---

## Technical Decisions

| # | Área | Pregunta | Decisión | Notas |
|---|------|----------|----------|-------|
| 1 | Payments | ¿Cómo procesar pagos? | **Stripe** | Subscriptions API + Checkout |
| 2 | Checkout | ¿Custom o hosted? | **Stripe Checkout (hosted)** | Menos código, PCI compliance automático |
| 3 | Portal | ¿Custom billing portal? | **Stripe Customer Portal** | Update payment method, download invoices |
| 4 | Plans | ¿Cómo definir planes? | **Stripe Products + Prices** | Planes en Stripe, sync con DB local |
| 5 | Trial | ¿Cómo manejar trial? | **Subscription con trial_period** | 14 días, luego cobra automático |
| 6 | Overage | ¿Cómo cobrar excesos? | **Stripe metered billing** | Reportar usage, Stripe calcula cobro |
| 7 | Proration | ¿Prorrateado en cambio de plan? | **Stripe automático** | `proration_behavior: create_prorations` |
| 8 | Webhooks | ¿Qué eventos procesar? | **Ver lista abajo** | checkout.session.completed, invoice.paid, etc |
| 9 | DB Sync | ¿Cómo sincronizar con Stripe? | **Webhook-driven** | No polling, estado siempre actualizado |
| 10 | Frontend | ¿Dónde mostrar billing? | **Dashboard /settings/billing** | Con info de plan, consumo, próximo cobro |

### Stripe Webhooks a procesar:
- `checkout.session.completed` - Suscripción creada
- `invoice.paid` - Pago exitoso
- `invoice.payment_failed` - Pago fallido
- `customer.subscription.updated` - Cambio de plan
- `customer.subscription.deleted` - Cancelación

---

## Scope

### In Scope (MVP)
- Trial de 14 días automático para nuevos usuarios
- 4 planes: 3 individuales + 1 bundle
- Integración Stripe Checkout para pagos
- Stripe Customer Portal para gestión
- Webhooks para sincronización de estado
- UI de billing en dashboard
- Overage reporting a Stripe
- Upgrade/downgrade de plan
- Cancelación de suscripción

### Out of Scope
- Múltiples métodos de pago (solo tarjeta)
- Facturación anual (v1.1)
- Cupones y descuentos (v1.1)
- Enterprise custom pricing (v2)
- Impuestos automáticos por región (v1.1)
- Team billing / multi-seat (v2)

---

## Dependencies

### Requires (this feature needs)
- [x] FEAT-001 - Auth & Onboarding (user accounts, tenant_id)
- [x] ARCH: PostgreSQL database (ADR-003)
- [x] ARCH: FastAPI backend (ADR-002)
- [x] External: Stripe Account configured

### Blocks (features that need this)
- FEAT-008 - Usage Tracking (necesita plan limits)
- Todos los agentes (necesitan verificar plan activo)

---

## Data Model

### Subscription Status Flow
```
TRIAL (14 días) → ACTIVE (pagando) → CANCELED (fin de período)
       ↓              ↓
   EXPIRED         PAST_DUE (reintento)
```

### Core Entities

```python
# Plan (sincronizado desde Stripe)
class Plan:
    id: str                    # stripe_price_id
    name: str                  # "InboxPilot", "Bundle", etc
    price_cents: int           # 2900, 4900
    interval: str              # "month"
    agents_included: list[str] # ["inbox"], ["inbox","invoice","meeting"]
    limits: dict               # {"emails_per_month": 500, ...}

# Subscription (estado local)
class Subscription:
    id: UUID
    tenant_id: UUID            # FK to tenant
    stripe_subscription_id: str
    stripe_customer_id: str
    plan_id: str               # FK to Plan
    status: str                # trial, active, past_due, canceled, expired
    trial_ends_at: datetime
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: datetime

# Invoice (histórico de pagos)
class Invoice:
    id: UUID
    tenant_id: UUID
    stripe_invoice_id: str
    subscription_id: UUID
    amount_cents: int
    status: str                # draft, open, paid, void, uncollectible
    period_start: datetime
    period_end: datetime
    paid_at: datetime | None
    hosted_invoice_url: str
    created_at: datetime
```

---

## API Design

### Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/billing/plans` | Listar planes disponibles | Public |
| GET | `/api/v1/billing/subscription` | Obtener suscripción actual | Required |
| POST | `/api/v1/billing/checkout` | Crear Stripe Checkout session | Required |
| POST | `/api/v1/billing/portal` | Crear Stripe Portal session | Required |
| POST | `/api/v1/billing/webhook` | Recibir eventos Stripe | Stripe signature |
| GET | `/api/v1/billing/invoices` | Listar facturas del tenant | Required |
| GET | `/api/v1/billing/usage` | Ver consumo actual | Required |

### Request/Response Examples

```json
// GET /api/v1/billing/subscription
// Response 200
{
  "subscription": {
    "id": "sub_xxx",
    "status": "active",
    "plan": {
      "id": "price_xxx",
      "name": "Bundle",
      "price": 4900,
      "agents": ["inbox", "invoice", "meeting"]
    },
    "trial_ends_at": null,
    "current_period_end": "2026-02-28T00:00:00Z",
    "cancel_at_period_end": false
  },
  "usage": {
    "emails_processed": 234,
    "emails_limit": 500,
    "invoices_processed": 12,
    "invoices_limit": 50,
    "meetings_processed": 8,
    "meetings_limit": 30
  }
}

// POST /api/v1/billing/checkout
// Request
{
  "price_id": "price_xxx",
  "success_url": "https://app.founderpilot.com/billing/success",
  "cancel_url": "https://app.founderpilot.com/billing"
}

// Response 200
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_xxx"
}

// POST /api/v1/billing/portal
// Response 200
{
  "portal_url": "https://billing.stripe.com/p/session/xxx"
}
```

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Trial expira sin pago | Status → expired, agentes desactivados, mostrar CTA suscribirse |
| Pago falla | Status → past_due, Stripe reintenta 3x, notificar usuario |
| Webhook duplicado | Idempotencia por stripe_event_id |
| Usuario cancela | cancel_at_period_end = true, sigue activo hasta fin de período |
| Downgrade a plan sin agente activo | Agente se desactiva al inicio del nuevo período |
| Overage muy alto | Límite de seguridad: máx 2x del límite base |

---

## UI/UX Decisions

| Elemento | Decisión | Referencia |
|----------|----------|------------|
| Trial banner | Banner sticky en dashboard mostrando días restantes | - |
| Pricing cards | 4 cards comparativas (3 individuales + bundle destacado) | - |
| Upgrade CTA | En cada agente si no está incluido en plan | - |
| Billing page | /settings/billing con plan, consumo, facturas | - |
| Usage bar | Barra de progreso por agente mostrando consumo vs límite | - |

---

## Security Considerations

- [x] Webhook verificado con Stripe signature (STRIPE_WEBHOOK_SECRET)
- [x] No almacenar datos de tarjeta (Stripe maneja PCI)
- [x] Endpoints de billing requieren autenticación
- [x] Validar tenant_id en todas las operaciones
- [x] Rate limiting en endpoint de webhook (por IP)
- [x] Logs de auditoría para cambios de suscripción

---

## Stripe Configuration Required

### Products & Prices (crear en Stripe Dashboard)
```
Product: InboxPilot
  - Price: $29/month (price_inboxpilot_monthly)

Product: InvoicePilot
  - Price: $19/month (price_invoicepilot_monthly)

Product: MeetingPilot
  - Price: $19/month (price_meetingpilot_monthly)

Product: FounderPilot Bundle
  - Price: $49/month (price_bundle_monthly)
```

### Environment Variables
```env
STRIPE_SECRET_KEY=sk_xxx
STRIPE_PUBLISHABLE_KEY=pk_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_INBOX=price_xxx
STRIPE_PRICE_INVOICE=price_xxx
STRIPE_PRICE_MEETING=price_xxx
STRIPE_PRICE_BUNDLE=price_xxx
```

---

## Open Questions

- [x] ¿Trial requiere tarjeta? → **No, trial sin tarjeta**
- [x] ¿Qué pasa si trial expira? → **Acceso bloqueado, debe suscribirse**
- [x] ¿Overage límite? → **Máximo 2x del límite base por seguridad**

---

## Interview Log

### Session 1 - 2026-01-31 (Ralph Loop - Autonomous)

**Discutido:**
- Pricing model: $29 InboxPilot, $19 InvoicePilot, $19 MeetingPilot, $49 Bundle
- Trial: 14 días sin tarjeta, acceso completo
- Stripe integration: Checkout hosted, Customer Portal, Webhooks
- Overage: $0.02/email, $0.10/invoice, $0.15/meeting (via metered billing)

**Decisiones:**
- Stripe Checkout para minimizar código y PCI compliance
- Stripe Customer Portal para gestión de pagos
- Webhook-driven sync (no polling)
- Overage con límite de seguridad 2x

**Fuentes:**
- docs/project.md (pricing, business model)
- docs/discovery/story-mapping-founderops.md (customer journey)

---

*Status: Interview Complete*
*Created: 2026-01-31*
*Last updated: 2026-01-31*
