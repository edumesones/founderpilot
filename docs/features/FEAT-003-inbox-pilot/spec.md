# FEAT-003: InboxPilot

## Summary

InboxPilot es el agente principal de FounderPilot que automatiza el triage de email para founders. Conecta con Gmail, clasifica emails por prioridad/tipo, draftea respuestas para emails rutinarios, y escala a Slack cuando la confianza es baja o el email requiere atención humana. Objetivo: reducir de 2h/dia a 20min el tiempo que un founder gasta en email.

---

## User Stories

- [x] Como **founder** quiero **conectar mi cuenta de Gmail** para **que el agente pueda acceder a mi inbox**
- [x] Como **founder** quiero **que el agente clasifique mis emails automáticamente** para **ver primero lo importante**
- [x] Como **founder** quiero **recibir drafts de respuestas para emails rutinarios** para **responder en un click**
- [x] Como **founder** quiero **ser notificado en Slack de emails urgentes** para **no perderme nada importante**
- [x] Como **founder** quiero **aprobar/editar drafts antes de enviar** para **mantener control de mi comunicación**
- [x] Como **founder** quiero **configurar reglas de clasificación** para **personalizar qué es importante para mí**
- [x] Como **founder** quiero **ver el historial de acciones del agente** para **entender qué ha hecho**

---

## Acceptance Criteria

- [x] Gmail OAuth funciona y obtiene tokens con scopes necesarios (readonly + send)
- [x] El agente procesa nuevos emails en < 30 segundos desde recepción
- [x] Clasificación tiene accuracy > 85% en categorías: urgent, important, routine, spam
- [x] Drafts se generan solo para emails clasificados como "routine" con confianza > 70%
- [x] Escalation a Slack ocurre cuando confianza < 80% o categoria es "urgent"
- [x] Usuario puede aprobar/rechazar/editar draft desde Slack
- [x] Cada acción del agente queda registrada en audit log
- [x] Workflow se puede pausar/reanudar (checkpointer)
- [x] Rate limits respetan quotas de Gmail API (250 units/sec)

---

## Technical Decisions

| # | Area | Pregunta | Decision | Notas |
|---|------|----------|----------|-------|
| 1 | Trigger | Como detectar nuevos emails? | Gmail Push Notifications (Pub/Sub) + polling fallback | Watch API con webhook |
| 2 | Classification | Modelo para clasificar? | GPT-4o-mini (fast, cheap) | Prompt con ejemplos |
| 3 | Drafting | Modelo para respuestas? | Claude 3.5 Sonnet (quality) | Mejor para escritura |
| 4 | State | Donde guardar estado del workflow? | PostgreSQL checkpointer (LangGraph) | Persistent, queryable |
| 5 | Escalation | Canal de escalation? | Slack DM al usuario | Con action buttons |
| 6 | Batch | Procesar 1 email o batch? | Individual (real-time feel) | Batch para digest futuro |
| 7 | Threading | Analizar thread completo? | Si, ultimos 5 mensajes | Contexto necesario |
| 8 | Attachments | Procesar attachments? | No en MVP | Solo metadata |
| 9 | Labels | Usar labels de Gmail? | Si, crear labels propios | FP_Urgent, FP_Draft, etc |

---

## Scope

### In Scope (MVP)

- Gmail OAuth connection flow
- Gmail Push Notifications setup (watch)
- Email fetch con thread context
- Email classification (4 categorias)
- Draft generation para routine emails
- Slack notification para urgent/low-confidence
- Approve/Reject/Edit actions desde Slack
- Send draft o archive
- Audit log de todas las acciones
- Agent configuration (thresholds, preferences)
- Gmail labels management

### Out of Scope

- Outlook integration (v1.1)
- Email scheduling
- Bulk actions UI
- Auto-unsubscribe
- Email analytics dashboard
- Multi-inbox (multiple Gmail accounts)
- Custom classification categories
- Attachment processing

---

## Dependencies

### Requires (this feature needs)

- [x] FEAT-001 - Auth & Onboarding (Google OAuth, user model)
- [x] FEAT-006 - Slack Integration (notifications, actions)
- [x] ARCH-001 - LangGraph agent base class
- [x] ARCH-003 - PostgreSQL setup
- [x] ARCH-004 - Redis + Celery setup
- [x] ARCH-008 - Langfuse setup

### Blocks (features that need this)

- FEAT-004 - InvoicePilot (usa email classification para detectar facturas)
- FEAT-007 - Audit Dashboard (muestra acciones de InboxPilot)

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Gmail token expired | Refresh token automático, si falla notificar usuario |
| Gmail rate limit hit | Exponential backoff, queue emails for retry |
| LLM API down | Fallback a otro provider, o escalar todo a humano |
| Email en idioma no soportado | Clasificar como "review needed", escalar |
| Email muy largo (>10k chars) | Truncar, incluir nota de truncamiento |
| Thread con 50+ emails | Solo ultimos 5 messages |
| Usuario no responde en Slack | Timeout 24h, archivar sin acción |
| Draft rechazado 3 veces seguidas | Pausar agente, pedir feedback |
| Duplicate webhook | Idempotency check por message_id |
| Email sin body (solo subject) | Clasificar solo con subject |

---

## UI/UX Decisions

| Elemento | Decision | Referencia |
|----------|----------|------------|
| Slack notification | Card con subject, snippet, sender, buttons | Slack Block Kit |
| Draft preview | Full draft en Slack, con diff si es reply | Mrkdwn format |
| Approval buttons | Approve / Edit / Reject / Archive | Action buttons |
| Edit flow | Modal con textarea editable | Slack modal |
| Dashboard | Ver lista de emails procesados, status | Next.js page |

---

## Security Considerations

- [x] Requiere autenticación (JWT + user context)
- [x] Gmail tokens encriptados at rest (AES-256)
- [x] Refresh tokens en secrets manager
- [x] Solo acceso a propio inbox (tenant isolation)
- [x] Rate limiting por usuario (50 emails/hour en trial)
- [x] GDPR: usuario puede exportar/borrar datos
- [x] No logging de email bodies completos (solo snippets para audit)
- [x] Scopes minimos necesarios de Gmail

---

## Open Questions

- [x] Batch processing para trial/free tier? -> No, same experience
- [x] Como manejar newsletters? -> Categoria "routine", auto-archive option
- [x] Idiomas soportados? -> EN/ES en MVP, detectar automaticamente

---

## Interview Log

### Session 1 - 2026-01-31

- Discutido: Core flow de InboxPilot basado en arquitectura existente
- Decisiones: Gmail Push > Polling, GPT-4o-mini para classify, Sonnet para draft
- Pendiente: Nada, spec completo

---

*Status: Interview Complete*
*Created: 2026-01-31*
*Last updated: 2026-01-31*
