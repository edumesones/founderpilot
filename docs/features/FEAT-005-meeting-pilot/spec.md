# FEAT-005: MeetingPilot

## Summary

MeetingPilot es un agente autónomo que prepara a founders para sus reuniones. Monitorea Google Calendar, detecta meetings próximos, recopila contexto relevante de emails/historial, genera un brief pre-call, y después de la reunión facilita follow-up actions.

---

## User Stories

- [x] Como **founder** quiero **recibir un brief de contexto 30 min antes de cada call** para **llegar preparado sin buscar información manualmente**
- [x] Como **founder** quiero **ver el historial de comunicación con cada participante** para **recordar de qué hablamos la última vez**
- [x] Como **founder** quiero **recibir sugerencias de follow-up después de calls** para **no olvidar compromisos**
- [x] Como **founder** quiero **que el agente aprenda mis patrones de meetings** para **mejorar los briefs con el tiempo**

---

## Acceptance Criteria

- [x] El agente detecta meetings del Google Calendar automáticamente
- [x] Genera brief de contexto con: participantes, historial de emails, notas previas, objetivos
- [x] Notifica via Slack 30 minutos antes del meeting
- [x] Permite al usuario añadir notas pre-meeting
- [x] Ofrece template de follow-up post-meeting
- [x] Respeta límites del plan (30 meetings/mes para MeetingPilot solo)
- [x] Todo queda registrado en audit log

---

## Technical Decisions

| # | Área | Pregunta | Decisión | Notas |
|---|------|----------|----------|-------|
| 1 | Calendar | ¿Qué calendarios soportar? | Google Calendar únicamente (v1) | Outlook en v1.1 |
| 2 | Timing | ¿Cuándo enviar el brief? | 30 min antes por defecto, configurable | Via preferencias de usuario |
| 3 | Context | ¿De dónde sacar contexto? | Gmail (emails con participantes) + notas guardadas | Integración con InboxPilot |
| 4 | Notification | ¿Cómo notificar? | Slack DM con botones de acción | Consistente con otros agentes |
| 5 | Storage | ¿Dónde guardar notas? | PostgreSQL tabla `meeting_notes` | Por tenant, vinculado a meeting_id |
| 6 | LLM | ¿Qué modelo para resumen? | Claude Haiku (costo-eficiente) | Upgrade a Sonnet si confianza baja |
| 7 | Sync | ¿Frecuencia de sincronización? | Cada 15 minutos | Celery beat schedule |
| 8 | Follow-up | ¿Cómo detectar action items? | LLM analiza notas post-meeting | Usuario confirma antes de crear tasks |

---

## Scope

### In Scope (MVP)

- Sincronización con Google Calendar (OAuth)
- Detección de meetings con participantes externos
- Generación de brief pre-meeting:
  - Lista de participantes con roles (si conocidos)
  - Últimos 5 emails intercambiados con cada participante
  - Notas de meetings anteriores con mismos participantes
  - Objetivos sugeridos basados en contexto
- Notificación Slack 30 min antes
- Botones: "Ver brief completo" | "Añadir nota" | "Snooze"
- Input de notas post-meeting
- Sugerencia de follow-up actions
- Tracking de uso (meetings procesados por mes)
- Audit log de todas las acciones

### Out of Scope

- Outlook/Exchange integration (FEAT-005-v2)
- Transcripción de meetings en vivo
- Grabación de audio/video
- Integración con Zoom/Meet para metadata
- Scheduling/booking de meetings
- Recurring meeting templates
- Team calendar sharing

---

## Dependencies

### Requires (this feature needs)

- [x] FEAT-001 - Auth & Onboarding (Google OAuth base)
- [x] FEAT-006 - Slack Integration (canal de notificación)
- [x] Google Calendar API access (adicional a Gmail)
- [x] Database schemas de tenant y audit

### Blocks (features that need this)

- FEAT-007 - Audit Dashboard (mostrará acciones de MeetingPilot)

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Meeting sin participantes externos | Ignorar (solo internal = no brief) |
| Participante sin historial | Brief indica "Primer contacto" |
| Calendar desconectado | Notificar usuario, ofrecer reconectar |
| Múltiples meetings simultáneos | Priorizar por: 1) VIP contacts, 2) más reciente |
| Meeting cancelado después de brief | Notificar cancelación, archivar brief |
| Usuario no responde al brief | No acción, solo loguear |
| Rate limit de Calendar API | Exponential backoff, máx 3 retries |
| Meeting en < 30 min al sincronizar | Enviar brief inmediatamente |

---

## UI/UX Decisions

| Elemento | Decisión | Referencia |
|----------|----------|------------|
| Brief format | Markdown estructurado en Slack | Similar a InboxPilot drafts |
| Colores | Confidence: 🟢 >80%, 🟡 50-80%, 🔴 <50% | Consistente con otros agentes |
| Botones Slack | Primary: "Ver brief", Secondary: "Añadir nota", "Snooze" | Block Kit buttons |
| Dashboard | Card en Audit Dashboard con próximos meetings | Diseñar con FEAT-007 |

---

## Security Considerations

- [x] Requiere autenticación (OAuth token válido)
- [x] Datos sensibles: contenido de emails, nombres de participantes
- [x] Calendar API scopes mínimos: `calendar.readonly`
- [x] No almacenar contenido de emails, solo metadata y resúmenes
- [x] GDPR: usuario puede eliminar todos sus datos de meeting
- [x] Rate limiting: máx 30 meetings/mes en plan individual
- [x] Audit log inmutable de todas las acciones

---

## Open Questions

- [x] ¿Incluir meetings recurrentes? → Sí, cada instancia es un meeting
- [x] ¿Brief para 1:1s internos? → No por defecto, configurable
- [x] ¿Integrar con InboxPilot para contexto? → Sí, compartir tenant emails

---

## Interview Log

### Session 1 - 2026-02-02 (Ralph Loop)

**Discussed:**
- Definición completa de MeetingPilot basada en project.md y story mapping
- Decisiones técnicas alineadas con arquitectura existente (LangGraph, FastAPI, Slack)
- Scope MVP vs futuro

**Decisions:**
- Google Calendar only para v1
- Brief 30 min antes (configurable)
- Contexto de Gmail + notas anteriores
- Notificación via Slack con botones de acción
- 30 meetings/mes límite en plan individual

**Pending:**
- Ninguno - spec completa para análisis crítico

---

*Status: Interview Complete*
*Created: 2026-02-02*
*Last updated: 2026-02-02*
