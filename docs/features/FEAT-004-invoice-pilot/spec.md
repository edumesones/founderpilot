# FEAT-004: InvoicePilot

## Summary

InvoicePilot es un agente autónomo que ayuda a founders a nunca olvidar cobrar una factura. Detecta facturas pendientes en el inbox (Gmail), trackea su estado de pago (pendiente/parcial/pagado), envía reminders automáticos al cliente cuando se acerca el vencimiento o se pasa, y escala al founder solo cuando hay incertidumbre o cuando se requiere acción manual. El agente mantiene un dashboard de facturas pendientes con montos, fechas de vencimiento y historial de seguimiento, integrándose con Slack para notificaciones y acciones rápidas.

El valor clave: Transformar el seguimiento manual de facturas (hojas de cálculo, recordatorios mentales, emails olvidados) en un sistema automático, transparente y auditable que mantiene el flujo de caja saludable sin esfuerzo adicional del founder.

---

## User Stories

- [ ] Como **founder** quiero **que el agente detecte automáticamente facturas que envío** para **no tener que trackearlas manualmente**
- [ ] Como **founder** quiero **ver un dashboard de todas mis facturas pendientes con montos y vencimientos** para **saber exactamente qué debo cobrar**
- [ ] Como **founder** quiero **que el agente me notifique cuando una factura está por vencer (3 días antes)** para **poder planificar mi flujo de caja**
- [ ] Como **founder** quiero **que el agente envíe reminders automáticos cuando una factura está vencida** para **no tener que perseguir manualmente a clientes**
- [ ] Como **founder** quiero **aprobar/editar los reminders antes de que se envíen** para **mantener control sobre la comunicación con clientes**
- [ ] Como **founder** quiero **marcar facturas como pagadas (total o parcialmente)** para **mantener el tracking actualizado**
- [ ] Como **founder** quiero **ver historial de reminders enviados por factura** para **saber cuántas veces he contactado al cliente**
- [ ] Como **founder** quiero **configurar días de reminder después de vencimiento** para **ajustar la agresividad del seguimiento**
- [ ] Como **founder** quiero **que el agente escale a Slack cuando detecta patrones problemáticos** para **identificar clientes morosos rápidamente**

---

## Acceptance Criteria

- [ ] Agente detecta facturas salientes en Gmail (emails con PDFs adjuntos de facturas o menciones de invoice/factura)
- [ ] Extrae datos clave: monto, moneda, fecha de emisión, fecha de vencimiento, cliente (email/nombre), número de factura
- [ ] Si datos son ambiguos (confianza < 80%), escala a Slack para confirmación manual
- [ ] Crea registro en DB con status: `pending`, `partial`, `paid`
- [ ] Dashboard muestra lista de facturas pendientes ordenadas por vencimiento
- [ ] Notificación Slack 3 días antes de vencimiento: "Factura X de $Y vence en 3 días"
- [ ] Reminder automático D+3, D+7, D+14 después de vencimiento (configurable)
- [ ] Reminder incluye: referencia original, monto pendiente, días vencidos, mensaje personalizado
- [ ] Founder puede aprobar/editar/rechazar reminder desde Slack antes de envío
- [ ] Founder puede marcar factura como pagada (total o parcial) desde dashboard o Slack
- [ ] Historial de acciones del agente por factura (detectada, reminder enviado, pagada)
- [ ] Audit log inmutable de cada acción del agente
- [ ] Integración con billing plan: límite de 50 invoices/mes en plan individual

---

## Technical Decisions

| # | Área | Pregunta | Decisión | Notas |
|---|------|----------|----------|-------|
| 1 | Detection | ¿Cómo detectar facturas? | **LLM + PDF parsing + heuristics** | Email subject/body con keywords ("invoice", "factura") + attachments PDF + análisis LLM del contenido |
| 2 | Extraction | ¿Cómo extraer datos de facturas? | **LLM multi-modal (GPT-4o/Claude Sonnet)** | Enviar PDF al LLM con structured output (amount, due_date, client, etc) |
| 3 | Confidence | ¿Cuándo escalar detección? | **Confianza < 80%** | Si monto, cliente o fecha dudosos, pedir confirmación |
| 4 | Reminders | ¿Cuándo enviar reminders? | **D-3 (warning), D+3, D+7, D+14** | Configurable por usuario, default: 3 reminders post-vencimiento |
| 5 | Tone | ¿Qué tono usar en reminders? | **Profesional pero amigable** | Template personalizable: "Hi {client}, just a friendly reminder..." |
| 6 | Human approval | ¿Aprobar cada reminder? | **Sí, vía Slack** | Mostrar draft en Slack con [Approve/Edit/Skip] |
| 7 | Payment detection | ¿Detectar pagos automáticamente? | **No en MVP** | Manual mark-as-paid, auto-detection en v1.1 |
| 8 | Multi-currency | ¿Soportar múltiples monedas? | **Sí** | Guardar monto + currency (USD, EUR, GBP, etc) |
| 9 | Partial payments | ¿Soportar pagos parciales? | **Sí** | Campo `amount_paid` vs `amount_total`, status `partial` |
| 10 | Escalation patterns | ¿Cuándo escalar por morosidad? | **3+ reminders sin pago** | Notificar: "Invoice X has 3 reminders sent, no payment yet" |
| 11 | Data source | ¿Solo Gmail o múltiples fuentes? | **Solo Gmail en MVP** | Outlook/manual upload en v1.1 |
| 12 | Integration | ¿Integrar con Stripe/contabilidad? | **No en MVP** | Stripe Invoices API en v1.1 para auto-sync |

---

## Scope

### ✅ In Scope (MVP)

- Detección automática de facturas salientes en Gmail
- Extracción de datos clave (monto, vencimiento, cliente) con LLM
- Confirmación manual cuando confianza < 80%
- Dashboard de facturas pendientes (monto, cliente, vencimiento, días vencidos)
- Notificación pre-vencimiento (D-3)
- Reminders automáticos post-vencimiento (D+3, D+7, D+14)
- Aprobación de reminders vía Slack
- Mark-as-paid manual (total o parcial)
- Historial de reminders por factura
- Escalation por patrones problemáticos (3+ reminders)
- Audit log de todas las acciones
- Multi-currency support
- Configuración de schedule de reminders

### ❌ Out of Scope

- Detección automática de pagos recibidos (v1.1)
- Integración con Stripe Invoices API (v1.1)
- Integración con sistemas de contabilidad (QuickBooks, Xero) (v1.1)
- Soporte para Outlook/otros emails (v1.1)
- Upload manual de facturas (v1.1)
- Reportes de cash flow / AR aging (v1.2)
- Predicción de retrasos basada en historial (v1.2)
- Templates de reminder por cliente (v1.2)
- Integración con calendarios para payment terms (v2)

---

## Dependencies

### Requires (this feature needs)
- [x] FEAT-001 - Auth & Onboarding (Google OAuth, Gmail access)
- [x] FEAT-002 - Billing & Plans (plan limits: 50 invoices/month)
- [ ] FEAT-003 - InboxPilot (shared Gmail integration logic)
- [ ] FEAT-006 - Slack Integration (notifications, actions)
- [x] ARCH: LangGraph agents framework (ADR-001)
- [x] ARCH: PostgreSQL database (ADR-003)
- [x] ARCH: LLM multi-provider (ADR-007)
- [x] External: Gmail API access
- [x] External: LLM with vision/PDF parsing (GPT-4o or Claude Sonnet)

### Blocks (features that need this)
- FEAT-007 - Audit Dashboard (necesita invoices en audit log)
- FEAT-008 - Usage Tracking (track invoices_processed)

---

## Data Model

### Invoice Status Flow
```
DETECTED (initial) → PENDING (confirmed) → OVERDUE (past due_date) → PAID (or PARTIAL)
       ↓
   REJECTED (false positive)
```

### Core Entities

```python
# Invoice
class Invoice:
    id: UUID
    tenant_id: UUID                 # FK to tenant
    gmail_message_id: str           # Original email ID
    invoice_number: str | None      # Extracted from PDF/email
    client_name: str
    client_email: str
    amount_total: Decimal
    amount_paid: Decimal            # For partial payments
    currency: str                   # USD, EUR, GBP, etc
    issue_date: date
    due_date: date
    status: str                     # detected, pending, overdue, partial, paid, rejected
    pdf_url: str | None             # Attachment URL or storage path
    confidence: float               # 0-1 from LLM extraction
    notes: str | None               # User notes
    created_at: datetime
    updated_at: datetime

# InvoiceReminder
class InvoiceReminder:
    id: UUID
    invoice_id: UUID                # FK to Invoice
    scheduled_at: datetime          # When to send (or sent)
    sent_at: datetime | None
    type: str                       # pre_due, post_due_3d, post_due_7d, post_due_14d
    status: str                     # pending, approved, sent, skipped, rejected
    draft_message: str              # Generated reminder text
    final_message: str | None       # After human edit
    approved_by: str | None         # user_id if manual approval
    response_received: bool         # Did client respond?
    created_at: datetime

# InvoiceAction (audit trail)
class InvoiceAction:
    id: UUID
    invoice_id: UUID
    workflow_id: UUID | None        # FK to workflow_run
    action_type: str                # detected, confirmed, reminder_sent, marked_paid, etc
    actor: str                      # "agent" or user_id
    details: dict                   # JSON with action-specific data
    timestamp: datetime
```

---

## API Design

### Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/invoices` | List all invoices (filter by status) | Required |
| GET | `/api/v1/invoices/:id` | Get invoice details + reminders | Required |
| POST | `/api/v1/invoices/:id/confirm` | Confirm detected invoice (if confidence < 80%) | Required |
| POST | `/api/v1/invoices/:id/reject` | Reject false positive | Required |
| POST | `/api/v1/invoices/:id/mark-paid` | Mark as paid (total or partial) | Required |
| GET | `/api/v1/invoices/:id/reminders` | List reminders for invoice | Required |
| POST | `/api/v1/invoices/:id/reminders/:reminder_id/approve` | Approve reminder draft | Required |
| POST | `/api/v1/invoices/:id/reminders/:reminder_id/edit` | Edit and approve reminder | Required |
| POST | `/api/v1/invoices/:id/reminders/:reminder_id/skip` | Skip this reminder | Required |
| GET | `/api/v1/invoices/settings` | Get reminder settings | Required |
| PUT | `/api/v1/invoices/settings` | Update reminder schedule | Required |

### Request/Response Examples

```json
// GET /api/v1/invoices?status=pending,overdue
// Response 200
{
  "invoices": [
    {
      "id": "inv_123",
      "invoice_number": "INV-2026-001",
      "client_name": "Acme Corp",
      "client_email": "billing@acme.com",
      "amount_total": 5000.00,
      "amount_paid": 0,
      "currency": "USD",
      "issue_date": "2026-01-15",
      "due_date": "2026-02-15",
      "days_overdue": 5,
      "status": "overdue",
      "reminders_sent": 1,
      "last_reminder_at": "2026-02-18T10:00:00Z",
      "created_at": "2026-01-15T14:30:00Z"
    }
  ],
  "summary": {
    "total_pending": 15000.00,
    "total_overdue": 8500.00,
    "count_pending": 5,
    "count_overdue": 3
  }
}

// POST /api/v1/invoices/inv_123/mark-paid
// Request
{
  "amount_paid": 5000.00,
  "payment_date": "2026-02-20",
  "notes": "Wire transfer received"
}

// Response 200
{
  "invoice": {
    "id": "inv_123",
    "status": "paid",
    "amount_paid": 5000.00,
    "updated_at": "2026-02-20T15:45:00Z"
  }
}

// POST /api/v1/invoices/inv_123/reminders/rem_456/approve
// Response 200
{
  "reminder": {
    "id": "rem_456",
    "status": "approved",
    "scheduled_to_send_at": "2026-02-21T09:00:00Z"
  }
}
```

---

## LangGraph Agent Architecture

### InvoicePilotAgent Workflow

```python
class InvoicePilotAgent:
    """
    Agent for invoice tracking and reminder automation.

    States:
    - InvoiceDetectionState: Scanning inbox for invoices
    - ExtractionState: Extracting data from PDF/email
    - ConfirmationState: Human confirmation if needed
    - ReminderState: Scheduling and sending reminders
    """

    def build_graph(self):
        graph = StateGraph(InvoiceState)

        # Detection flow
        graph.add_node("scan_inbox", self.scan_inbox)          # Fetch sent emails
        graph.add_node("detect_invoice", self.detect_invoice)  # Identify invoice emails
        graph.add_node("extract_data", self.extract_data)      # Parse with LLM
        graph.add_node("confirm", self.confirm_invoice)        # Human validation if needed
        graph.add_node("store_invoice", self.store_invoice)    # Save to DB

        # Reminder flow
        graph.add_node("check_reminders", self.check_reminders_due)  # Daily check
        graph.add_node("draft_reminder", self.draft_reminder)        # Generate message
        graph.add_node("await_approval", self.await_approval)        # Human approval
        graph.add_node("send_reminder", self.send_reminder)          # Send via Gmail
        graph.add_node("log_action", self.log_action)                # Audit trail

        # Escalation flow
        graph.add_node("detect_pattern", self.detect_problem_pattern)  # 3+ reminders
        graph.add_node("escalate", self.escalate_to_slack)             # Notify founder

        # Conditional edges
        graph.add_conditional_edges(
            "extract_data",
            self.needs_confirmation,
            {"yes": "confirm", "no": "store_invoice"}
        )

        graph.add_conditional_edges(
            "draft_reminder",
            self.should_escalate,
            {"yes": "escalate", "no": "await_approval"}
        )

        return graph.compile(checkpointer=PostgresCheckpointer())
```

### LLM Prompts

**Invoice Detection Prompt:**
```
Analyze this email and determine if it contains an outgoing invoice.

Email subject: {subject}
Email body: {body}
Attachments: {attachments}

Is this an outgoing invoice? Consider:
- Keywords: invoice, factura, bill, payment due
- Sender is user (not received invoice)
- Has payment terms, amounts, due dates
- Professional format

Return JSON:
{
  "is_invoice": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "..."
}
```

**Data Extraction Prompt:**
```
Extract invoice data from this email and attached PDF.

Email: {email_text}
PDF content: {pdf_text or image}

Extract:
{
  "invoice_number": "string or null",
  "client_name": "string",
  "client_email": "string",
  "amount_total": float,
  "currency": "USD|EUR|GBP|etc",
  "issue_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "confidence": 0.0-1.0,
  "extraction_notes": "any uncertainties"
}

If any field is unclear, set confidence < 0.8 and explain in notes.
```

**Reminder Draft Prompt:**
```
Draft a friendly but professional payment reminder for this overdue invoice.

Invoice details:
- Client: {client_name}
- Amount: {amount} {currency}
- Due date: {due_date} (now {days_overdue} days overdue)
- Invoice number: {invoice_number}
- Previous reminders: {reminder_count}

Tone: {tone_setting}  # friendly, professional, firm
Relationship: {relationship}  # long-term client, new client, etc

Draft a 2-3 sentence reminder email that:
- References the original invoice
- States the overdue amount and days
- Politely requests payment
- Offers to help if there are issues

Return plain text email body (no subject line).
```

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| PDF unreadable/corrupted | Confidence = 0, escalate to Slack: "Invoice detected but can't read PDF" |
| Multiple currencies in one invoice | Extract all, flag for manual review |
| Client responds to reminder | Detect reply, pause reminder sequence, notify founder |
| Partial payment received | Update amount_paid, recalculate reminders for remaining balance |
| Invoice edited after detection | Allow manual edit in dashboard, log change |
| Duplicate invoice detected | Check gmail_message_id, skip if exists |
| User manually uploads invoice | Out of scope v1, but schema supports it (gmail_message_id null) |
| Reminder email bounces | Log bounce, escalate to Slack, pause reminders |
| Client has multiple invoices | Group by client in dashboard, allow batch reminder |
| Due date in past at detection | Immediately mark as overdue, schedule first reminder |
| No due date in invoice | Ask user to set due date during confirmation |
| Invoice amount is $0 | Flag for review (may be quote, not invoice) |

---

## UI/UX Decisions

| Elemento | Decisión | Referencia |
|----------|----------|------------|
| Dashboard layout | Table view: Client, Amount, Due Date, Days Overdue, Status, Actions | Similar to Stripe Invoices |
| Status colors | Green (paid), Yellow (pending), Red (overdue), Gray (partial) | Traffic light metaphor |
| Reminder approval | Slack message with inline actions: [✅ Send] [✏️ Edit] [⏰ Skip] | Same pattern as InboxPilot |
| Invoice details page | Timeline view: Detected → Reminders sent → Paid | Visual progress |
| Filter options | Status (pending/overdue/paid), Date range, Client, Amount range | Standard filters |
| Sort options | Due date (default), Amount, Days overdue, Client name | Most urgent first |
| Mark paid modal | Amount field (pre-filled), Date picker, Notes textarea | Quick action |
| Settings page | Reminder schedule (D-3, D+3, D+7, D+14), Tone (friendly/professional/firm) | Customization |
| Mobile view | Card-based layout, swipe actions (Mark paid, Send reminder) | Out of scope v1 |

---

## Slack Integration

### Notification Examples

**Invoice Detected (Low Confidence):**
```
🧾 InvoicePilot

New invoice detected, please confirm:

📧 From: email sent to billing@acme.com
💰 Amount: $5,000 USD
📅 Due: Feb 15, 2026
📎 Invoice: INV-2026-001.pdf

⚠️ Confidence: 65%
❓ Unclear: Due date format ambiguous

[✅ Confirm] [✏️ Edit] [❌ Not an Invoice]
```

**Reminder Approval:**
```
🔔 InvoicePilot - Reminder ready to send

Invoice: INV-2026-001
Client: Acme Corp (billing@acme.com)
Amount: $5,000 USD
Status: 5 days overdue

📝 Draft message:
"Hi Acme team, just a friendly reminder that invoice INV-2026-001
for $5,000 is now 5 days past due (due Feb 15). Could you please
confirm when we can expect payment? Let me know if you have any
questions. Thanks!"

[✅ Send Now] [✏️ Edit] [⏰ Snooze 3 days] [❌ Skip]
```

**Escalation (Problem Pattern):**
```
⚠️ InvoicePilot - Action needed

Invoice: INV-2026-001
Client: Acme Corp
Amount: $5,000 USD
Status: 21 days overdue

📊 Pattern:
- 3 reminders sent (Feb 18, Feb 22, Feb 25)
- No response from client
- No payment received

💡 Suggested actions:
- Call client directly
- Send final notice
- Consider late fees

[📞 Mark as Contacted] [📄 Final Notice] [View Details]
```

---

## Security Considerations

- [x] Autenticación requerida en todos los endpoints
- [x] Validar tenant_id en todas las queries (evitar acceso cross-tenant)
- [x] Datos de facturas son sensibles (montos, clientes) - no loggear montos en logs públicos
- [x] Rate limiting en detección (máx 100 invoices/day por tenant para evitar spam)
- [x] Validar que reminder solo se envíe a email del cliente (no a terceros)
- [x] Audit log inmutable para compliance (GDPR: derecho a saber qué se hizo con sus datos)
- [x] Encriptar PDFs at rest si contienen datos sensibles
- [x] No procesar invoices de otros usuarios (validar sender = authenticated user)
- [x] Prevenir injection en LLM prompts (sanitizar inputs)

---

## Performance Considerations

| Aspect | Target | Implementation |
|--------|--------|----------------|
| Invoice detection | 1 scan every 5 min | Celery beat task |
| Extraction latency | < 15s per invoice | LLM call + PDF parsing |
| Dashboard load | < 500ms | Indexed queries on due_date, status |
| Reminder scheduling | Daily batch at 9am | Celery beat task |
| Reminder send | < 5s per reminder | Async Gmail API |
| PDF storage | S3 with CDN | Pre-signed URLs for download |

---

## Celery Tasks

```python
# Detection task (every 5 minutes)
@celery.task
def scan_invoices_for_all_tenants():
    for tenant in get_active_tenants():
        InvoicePilotAgent(tenant_id=tenant.id).scan_inbox()

# Reminder task (daily at 9am)
@celery.task
def check_invoice_reminders():
    for tenant in get_active_tenants():
        InvoicePilotAgent(tenant_id=tenant.id).check_reminders_due()

# Escalation task (daily at 10am)
@celery.task
def check_problem_patterns():
    for tenant in get_active_tenants():
        InvoicePilotAgent(tenant_id=tenant.id).detect_problem_pattern()
```

---

## Testing Strategy

### Unit Tests
- Invoice detection logic (email parsing, keyword matching)
- LLM extraction parsing (mock LLM responses)
- Reminder scheduling logic (date calculations)
- Status transitions (pending → overdue → paid)

### Integration Tests
- Gmail API: fetch sent emails, send reminder
- LLM API: extraction with real PDF samples
- Slack API: send notification, handle action
- Database: CRUD operations, transactions

### E2E Tests
- Full flow: Send invoice email → Detect → Extract → Confirm → Schedule reminder → Send reminder → Mark paid
- Low confidence flow: Detect → Escalate → Human confirm → Store
- Escalation flow: 3 reminders → Pattern detected → Slack notification

### Test Data
- Sample invoice PDFs (various formats, currencies, languages)
- Edge cases: no due date, $0 amount, corrupted PDF
- Mock email threads with invoice + payment confirmation

---

## Migration Strategy

### Phase 1: Passive Detection (Week 1)
- Deploy detection logic, store invoices in DB
- No reminders sent yet
- Monitor for false positives
- Tune confidence thresholds

### Phase 2: Manual Reminders (Week 2)
- Enable draft reminder generation
- Require approval for ALL reminders
- Collect user feedback on tone/content

### Phase 3: Semi-Automatic (Week 3)
- Auto-send reminders with confidence > 90%
- Still require approval for < 90%
- Monitor bounce rates

### Phase 4: Full Automation (Week 4)
- Auto-send all scheduled reminders
- Escalate only on bounces or patterns
- Full production mode

---

## Open Questions

- [x] ¿Soportar invoice en idiomas no-inglés? → **Sí, LLM es multilingual**
- [x] ¿Detectar pagos desde bank feeds? → **No en MVP, v1.1**
- [x] ¿Integrar con Stripe Invoices API? → **No en MVP, v1.1**
- [ ] ¿Cuál es el límite de "agresividad" máxima? → **Máx 5 reminders, luego pausar y escalar**
- [ ] ¿Qué hacer si cliente pide dejar de mandar reminders? → **Marcar invoice como "paused", no enviar más**
- [ ] ¿Soportar late fees automáticos? → **No en MVP, calcular pero no aplicar**

---

## Interview Log

### Session 1 - 2026-02-02

**Discutido:**
- Core value: Founders olvidan cobrar → cash flow problem
- Detección con LLM (GPT-4o/Claude) + PDF parsing
- Reminders con human approval (mantener control)
- Escalation cuando 3+ reminders sin pago
- Multi-currency, partial payments
- Integration con FEAT-003 (shared Gmail logic), FEAT-006 (Slack)

**Decisiones:**
- LLM-based extraction (más flexible que regex)
- Confidence threshold 80% para auto-confirm
- Reminder schedule: D-3 (warning), D+3, D+7, D+14 (configurable)
- Manual mark-as-paid (auto-detection v1.1)
- Slack approval para reminders (same UX as InboxPilot)
- No Stripe integration en MVP (v1.1)

**Scope:**
- IN: Detection, extraction, reminders, approval, dashboard, audit
- OUT: Auto payment detection, Stripe API, Outlook, manual upload

**Fuentes:**
- docs/project.md (InvoicePilot description, pricing $19/month)
- docs/architecture/_index.md (LangGraph, LLM providers, audit pattern)
- docs/features/FEAT-002-billing-plans/spec.md (plan limits: 50 invoices/month)
- docs/discovery/story-mapping-founderops.md (Release 2: Invoice follow-up)

---

*Status: ✅ Interview Complete*
*Created: 2026-02-02*
*Last updated: 2026-02-02*
