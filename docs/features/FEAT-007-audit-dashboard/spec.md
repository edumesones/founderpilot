# FEAT-007: Audit Dashboard

## Summary

The Audit Dashboard provides complete transparency into all AI agent actions within FounderPilot. It displays a chronological, filterable view of every decision made by InboxPilot, InvoicePilot, and MeetingPilot, including the confidence level, input/output data, and whether human approval was required. This dashboard is critical for building trust with founders who need to verify that their AI agents are making appropriate decisions without blindly automating everything.

The dashboard serves two key purposes: (1) real-time monitoring of agent activity with the ability to rollback or override decisions, and (2) historical audit trail for compliance and debugging. By making every agent action transparent and auditable, we address the core concern from our research: "We automated everything and now nobody trusts anything."

---

## User Stories

- [ ] Como **founder** quiero **ver todas las acciones que mis agentes tomaron hoy** para **verificar que están funcionando correctamente**
- [ ] Como **founder** quiero **filtrar el audit log por agente (InboxPilot, InvoicePilot, MeetingPilot)** para **enfocarme en un área específica**
- [ ] Como **founder** quiero **ver el nivel de confianza de cada decisión** para **identificar cuándo el agente no estaba seguro**
- [ ] Como **founder** quiero **hacer clic en una acción y ver el detalle completo** para **entender exactamente qué consideró el agente**
- [ ] Como **founder** quiero **ver qué acciones escalaron a mí para aprobación** para **saber cuándo el agente necesitó ayuda**
- [ ] Como **founder** quiero **filtrar por rango de fechas** para **revisar actividad de días/semanas pasadas**
- [ ] Como **founder** quiero **ver el trace completo en Langfuse** para **debugging técnico profundo**
- [ ] Como **founder** quiero **rollback una acción** para **deshacer un error del agente**

---

## Acceptance Criteria

- [ ] Dashboard muestra audit log en orden cronológico inverso (más reciente primero)
- [ ] Cada entrada muestra: timestamp, agente, acción, confidence, status (auto/escalated/approved/rejected)
- [ ] Filtros funcionales: por agente, por fecha, por status, por nivel de confianza
- [ ] Vista detallada al hacer clic en una entrada: input completo, output completo, decisión, trace_id
- [ ] Indicador visual de confianza: verde (>90%), amarillo (70-90%), rojo (<70%)
- [ ] Link directo a Langfuse trace desde cada entrada
- [ ] Paginación o scroll infinito para manejar cientos de entradas
- [ ] Badge de "Escalated" visible en acciones que requirieron aprobación humana
- [ ] Tiempo de carga inicial < 2s para últimas 50 entradas
- [ ] Búsqueda de texto libre por contenido de input/output
- [ ] Export a CSV para auditoría externa
- [ ] Responsive design (funciona en mobile)

---

## Technical Decisions

| # | Área | Pregunta | Decisión | Notas |
|---|------|----------|----------|-------|
| 1 | Data Model | ¿Qué estructura tiene audit_log? | Table con: id, timestamp, user_id, workflow_id, agent_type, action, input_summary, output_summary, decision, confidence, escalated, authorized_by, trace_id, metadata (JSON) | PostgreSQL, índices en timestamp, user_id, agent_type |
| 2 | UI Framework | ¿Qué usar para el dashboard? | Next.js 14 con React Server Components + TanStack Table para tabla de datos | Server-side rendering inicial, luego client-side filtering |
| 3 | Filtros | ¿Cómo implementar filtros? | Query params en URL + React state para UI, API endpoint `/api/audit?agent=inbox&from=...&to=...` | URL shareable, browser back/forward funciona |
| 4 | Paginación | ¿Paginación o infinite scroll? | Cursor-based pagination (últimos 50, luego "Load more") | Más eficiente que offset-based en tablas grandes |
| 5 | Detalle | ¿Modal o página separada? | Modal slide-over (Headless UI) | Mantiene contexto, más rápido que navegación |
| 6 | Performance | ¿Cómo manejar miles de entradas? | PostgreSQL partial indexes + input/output truncados a 500 chars en lista, full data en detalle | Trade-off: mostrar snippet, cargar completo on-demand |
| 7 | Real-time | ¿Updates en tiempo real? | No para MVP, refresh manual | Post-MVP: WebSockets o polling cada 30s |
| 8 | Export | ¿Formato de export? | CSV con todas las columnas, límite 10k filas | Streaming response para no sobrecargar memoria |
| 9 | Rollback | ¿Qué significa "rollback"? | Marca entrada como "rolled_back", trigger workflow compensatorio (ej: unsend email, cancel reminder) | No es undo literal, es compensating action |
| 10 | Search | ¿Full-text search o simple LIKE? | PostgreSQL tsvector + GIN index en input/output | Buscar "invoice", "meeting", nombres, emails |
| 11 | Auth | ¿Quién puede ver el audit log? | Solo el user_id owner de las acciones | Multi-tenant: WHERE user_id = current_user |
| 12 | Confidence Display | ¿Cómo mostrar confianza? | Progress bar + color + número (ej: "87% - High") | Verde >90%, Amarillo 70-90%, Rojo <70% |

---

## Scope

### ✅ In Scope (MVP)

- Tabla principal con últimas 50 entradas por defecto
- Filtros: agente, rango de fechas, status (all/auto/escalated), min confidence
- Vista detallada en modal: input full, output full, metadata
- Búsqueda de texto libre (simple)
- Link a Langfuse trace
- Export CSV (básico)
- Indicadores visuales de confianza
- Badge "Escalated" para acciones con human approval
- Paginación "Load more" (cursor-based)
- Responsive mobile
- Data retention: 1 año

### ❌ Out of Scope

- Real-time updates (WebSockets) - Post-MVP
- Rollback automático con UI (botón "Undo") - Post-MVP
- Analytics dashboard (gráficos de tendencias) - Ver FEAT-008
- Notificaciones cuando confidence baja - Se hace en Slack (FEAT-006)
- Multi-user/team view - MVP es single user
- Advanced search (regex, filters avanzados) - Post-MVP
- Audit log para acciones de billing/auth - Solo agentes AI

---

## Dependencies

### Requires (this feature needs)
- [x] FEAT-001 - Auth & Onboarding (user_id, JWT middleware)
- [x] FEAT-002 - Billing & Plans (solo usuarios pagando pueden acceder)
- [x] FEAT-003 - InboxPilot (genera audit entries)
- [x] FEAT-004 - InvoicePilot (genera audit entries)
- [x] FEAT-005 - MeetingPilot (genera audit entries)
- [x] FEAT-006 - Slack Integration (links a mensajes de escalación)
- [ ] ARCH: audit_log table en PostgreSQL (crear migration)
- [ ] ARCH: Audit service en backend (write audit entries)
- [ ] ARCH: Langfuse integration (trace_id disponible)

### Blocks (features that need this)
- FEAT-008 - Usage Tracking (puede leer audit_log para analytics)
- Post-MVP: Compliance reports
- Post-MVP: Agent performance optimization

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| No hay entradas aún | Mostrar empty state: "No agent activity yet. Your agents will appear here once they start working." |
| Usuario nuevo sin agentes configurados | Mostrar empty state + link a setup |
| Input/output muy largo (>10k chars) | Truncar en lista, mostrar completo en modal con scroll, advertir "Large data - may take a moment" |
| trace_id no existe en Langfuse | Link disabled, tooltip "Trace not available" |
| Error al cargar audit log | Toast error "Failed to load audit log. Try again." + retry button |
| Filtros sin resultados | Mostrar "No results found for these filters" + clear filters button |
| Export CSV con >10k filas | Mostrar warning "Export limited to 10,000 rows. Use date filters to narrow down." |
| API timeout (lento) | Loading skeleton UI, timeout después 10s con error |
| Usuario no autorizado (wrong user_id) | 403 Forbidden, redirect a /login |
| Concurrent updates (race condition) | Usar optimistic locking o timestamp para detectar conflicts |

---

## UI/UX Decisions

| Elemento | Decisión | Referencia |
|----------|----------|------------|
| Layout | Dashboard con sidebar izq (nav), main area con tabla full-width | Similar a Vercel Analytics |
| Colores | Confidence colors: green (#10b981), yellow (#f59e0b), red (#ef4444) | Tailwind semantic colors |
| Tabla | TanStack Table (sortable columns, sticky header) | Virtualization si >1000 rows |
| Filtros | Dropdown (agent), date pickers (from/to), slider (min confidence), toggle (show escalated only) | Encima de tabla, horizontal layout |
| Modal | Slide-over desde derecha, 50% width, scroll inside | Headless UI SlideOver component |
| Empty state | Ilustración + texto + CTA | Heroicons illustration |
| Loading | Skeleton UI (shimmer effect) para initial load, spinner para "Load more" | react-loading-skeleton |
| Mobile | Tabla colapsa a cards, filtros en drawer | @media (max-width: 768px) |
| Badges | Pill shape, small text, icon prefixes (⚡ auto, 👤 escalated) | Subtle, no overwhelming |
| Export button | Top-right, icon + text "Export CSV" | Secondary button style |

---

## Security Considerations

- [x] **Requiere autenticación:** Sí, JWT obligatorio, redirect a /login si no autenticado
- [x] **¿Qué datos son sensibles?**
  - Input/output pueden contener emails, nombres, datos de facturas
  - Metadata puede tener tokens de APIs (debe ser sanitizado antes de guardar)
  - No exponer trace_id completo (solo hash) si contiene info sensible
- [x] **¿Necesita rate limiting?**
  - Sí, 100 requests/min por user_id en /api/audit
  - Export CSV: 5 requests/hour por user
- [x] **¿Cumple con GDPR/privacidad?**
  - Data retention: 1 año, luego auto-delete
  - User puede request "Delete all my audit logs" (GDPR right to erasure)
  - No compartir audit logs entre users (multi-tenant isolation)
  - Input/output sanitizado: no guardar passwords, tokens, PII no necesaria

---

## Data Model

### audit_log Table

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workflow_id UUID, -- LangGraph workflow run ID
    agent_type VARCHAR(50) NOT NULL, -- 'inbox_pilot', 'invoice_pilot', 'meeting_pilot'
    action VARCHAR(100) NOT NULL, -- 'classify_email', 'draft_response', 'send_reminder', etc.
    input_summary TEXT, -- Truncated input (max 2000 chars)
    output_summary TEXT, -- Truncated output (max 2000 chars)
    decision TEXT, -- Human-readable decision made
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    escalated BOOLEAN DEFAULT FALSE,
    authorized_by VARCHAR(50), -- 'agent' or user_id
    trace_id VARCHAR(255), -- Langfuse trace ID
    metadata JSONB, -- Full input/output, extra context
    rolled_back BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_log_user_timestamp ON audit_log(user_id, timestamp DESC);
CREATE INDEX idx_audit_log_agent_type ON audit_log(agent_type);
CREATE INDEX idx_audit_log_escalated ON audit_log(escalated) WHERE escalated = TRUE;
CREATE INDEX idx_audit_log_search ON audit_log USING GIN(to_tsvector('english', input_summary || ' ' || output_summary));
```

---

## API Endpoints

### GET /api/audit

**Query Params:**
- `agent` (optional): Filter by agent_type ('inbox_pilot', 'invoice_pilot', 'meeting_pilot')
- `from` (optional): ISO 8601 date (start range)
- `to` (optional): ISO 8601 date (end range)
- `min_confidence` (optional): Float 0-1 (minimum confidence)
- `escalated` (optional): Boolean (show only escalated)
- `search` (optional): Text search in input/output
- `cursor` (optional): Pagination cursor (last entry ID)
- `limit` (optional): Max entries (default 50, max 100)

**Response:**
```json
{
  "entries": [
    {
      "id": "uuid",
      "timestamp": "2026-02-02T10:30:00Z",
      "agent_type": "inbox_pilot",
      "action": "draft_response",
      "input_summary": "Email from john@example.com: Can we schedule...",
      "output_summary": "Draft: Hi John, Yes I can do Thursday at 3pm...",
      "decision": "Drafted response (high confidence)",
      "confidence": 0.92,
      "escalated": false,
      "authorized_by": "agent",
      "trace_id": "langfuse-trace-abc123"
    }
  ],
  "next_cursor": "uuid-last-entry",
  "has_more": true
}
```

### GET /api/audit/:id

**Response:**
```json
{
  "id": "uuid",
  "timestamp": "2026-02-02T10:30:00Z",
  "agent_type": "inbox_pilot",
  "action": "draft_response",
  "input_full": "Full email text...",
  "output_full": "Full draft text...",
  "decision": "Drafted response (high confidence)",
  "confidence": 0.92,
  "escalated": false,
  "authorized_by": "agent",
  "trace_id": "langfuse-trace-abc123",
  "metadata": {
    "email_id": "gmail-msg-123",
    "thread_id": "gmail-thread-456",
    "processing_time_ms": 2500,
    "llm_model": "claude-3-5-sonnet",
    "tokens_used": 1250
  }
}
```

### POST /api/audit/export

**Body:**
```json
{
  "filters": {
    "agent": "inbox_pilot",
    "from": "2026-01-01",
    "to": "2026-02-02"
  },
  "format": "csv"
}
```

**Response:** CSV file download (streaming)

---

## Open Questions

- [x] ¿Cómo detectar invoices? → Respondido en FEAT-004 (regex + LLM hybrid)
- [x] ¿Langfuse self-hosted o cloud? → Cloud para MVP (free tier), self-hosted post-MVP
- [ ] ¿Rollback debe ser automático o manual? → Manual para MVP, con confirmation modal

---

## Interview Log

### Session 1 - 2026-02-02

**Discutido:**
- Feature scope y user stories completadas
- Decisiones técnicas: audit_log schema, API design, UI framework
- Integración con Langfuse para traces
- Filtros y búsqueda: balance entre simplicidad (MVP) y utilidad
- Security: data retention, GDPR, multi-tenant isolation

**Decisiones:**
- PostgreSQL audit_log con índices optimizados para queries comunes
- Next.js + TanStack Table para UI rápida y escalable
- Cursor-based pagination (mejor performance que offset)
- CSV export con límite 10k filas (evitar timeout)
- Full-text search con tsvector (suficiente para MVP)
- Confidence display: progress bar + color coding
- Modal slide-over para detalle (mejor UX que página separada)
- No real-time updates en MVP (simplifica arquitectura)

**Pendiente:**
- Definir UX exact para rollback (si se incluye en MVP)
- Validar performance de full-text search con 100k+ entries (post-MVP)

---

*Status: ✅ Interview Complete*
*Created: 2026-02-02*
*Last updated: 2026-02-02*
