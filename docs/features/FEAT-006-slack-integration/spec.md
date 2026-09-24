# FEAT-006: Slack Integration

## Summary

Slack Integration enables FounderPilot to communicate with founders through Slack - the primary channel for notifications, escalations, and quick actions. When agents (InboxPilot, InvoicePilot, MeetingPilot) need human input or want to report results, they send formatted messages to Slack with interactive buttons. Users can approve, reject, or edit proposed actions directly from Slack without opening a browser.

---

## User Stories

- [x] Como **founder** quiero **conectar mi workspace de Slack** para **recibir notificaciones de los agentes**
- [x] Como **founder** quiero **recibir mensajes cuando un agente necesita mi input** para **mantener el control sin revisar constantemente**
- [x] Como **founder** quiero **aprobar/rechazar acciones desde Slack** para **actuar rápidamente sin cambiar de contexto**
- [x] Como **founder** quiero **editar respuestas propuestas en Slack** para **ajustar antes de enviar**
- [x] Como **founder** quiero **ver el contexto completo de cada escalación** para **tomar decisiones informadas**

---

## Acceptance Criteria

- [x] AC1: Usuario puede instalar la app de Slack via OAuth desde el dashboard
- [x] AC2: Bot envía mensaje de bienvenida al usuario tras conexión exitosa
- [x] AC3: Agentes pueden enviar notificaciones formateadas con bloques de Slack
- [x] AC4: Mensajes incluyen botones interactivos (Approve, Reject, Edit, Snooze)
- [x] AC5: Clicks en botones disparan callbacks que actualizan el workflow
- [x] AC6: Mensaje se actualiza tras la acción del usuario (confirmación visual)
- [x] AC7: Errores de Slack se loguean y el sistema reintenta con backoff
- [x] AC8: Tokens de Slack se almacenan cifrados y se refrescan automáticamente

---

## Technical Decisions

| # | Área | Pregunta | Decisión | Notas |
|---|------|----------|----------|-------|
| 1 | Framework | ¿Qué librería usar para Slack? | **Slack Bolt (Python)** | Oficial de Slack, maneja OAuth, events, interactivity |
| 2 | Auth | ¿Cómo almacenar tokens? | **PostgreSQL cifrado** | slack_installations table con AES encryption |
| 3 | Events | ¿Webhook o Socket Mode? | **Socket Mode** | No requiere URL pública, ideal para desarrollo |
| 4 | Messages | ¿Formato de mensajes? | **Block Kit** | Rich formatting, buttons, modals |
| 5 | Callbacks | ¿Cómo procesar interacciones? | **Slack Bolt handlers** | action_id based routing |
| 6 | State | ¿Cómo vincular acción a workflow? | **action_id = workflow_id** | Callback incluye workflow_id para lookup |
| 7 | Retry | ¿Cómo manejar fallos? | **Celery retry con exponential backoff** | Max 3 retries, delays: 1s, 5s, 30s |

---

## Scope

### ✅ In Scope (MVP)

- Slack OAuth 2.0 flow para instalación
- Almacenamiento seguro de access_token y bot_token
- Bot DM para notificaciones 1:1 con usuario
- Block Kit messages con formatting rico
- Interactive buttons: Approve, Reject, Edit, Snooze
- Modal para editar respuestas propuestas
- Callback handlers para cada acción
- Message updates post-acción (confirmación visual)
- Error handling y retry logic
- Integration con audit_log (cada acción se registra)

### ❌ Out of Scope

- Slash commands (ver FEAT-XXX futuro)
- Channel posting (solo DMs por ahora)
- Slack Enterprise Grid (v2)
- Home tab con dashboard (v2)
- Scheduled messages (los agentes deciden timing)
- Mentions y threading (simplicidad MVP)

---

## Dependencies

### Requires (this feature needs)

- [x] FEAT-001 - Auth & Onboarding (user account must exist)
- [x] ARCH-003 - PostgreSQL database for storing tokens
- [x] ARCH-004 - Redis for Celery (async message sending)
- [ ] Slack App created in Slack API dashboard
- [ ] Socket Mode enabled in Slack App settings

### Blocks (features that need this)

- FEAT-003 - InboxPilot (uses Slack for escalations)
- FEAT-004 - InvoicePilot (uses Slack for payment reminders)
- FEAT-005 - MeetingPilot (uses Slack for meeting prep alerts)
- FEAT-007 - Audit Dashboard (shows Slack interactions)

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| Token expirado | Refresh automático; si falla, notificar vía email |
| Usuario desinstala app | Marcar como desconectado, pausar agentes |
| Slack API timeout | Retry con exponential backoff (max 3) |
| Rate limit (429) | Respetar Retry-After header, queue mensajes |
| Botón clickeado 2 veces | Idempotencia - segunda acción es no-op |
| Workflow ya completado | Mostrar mensaje "Action already processed" |
| Usuario en múltiples workspaces | Soportar, pero MVP: 1 workspace por user |

---

## UI/UX Decisions

| Elemento | Decisión | Referencia |
|----------|----------|------------|
| Message format | Block Kit con secciones claras | Slack Block Kit Builder |
| Button colors | Primary (Approve), Default (Edit, Snooze), Danger (Reject) | Slack button styles |
| Confirmation | Update message con checkmark y texto de confirmación | Ephemeral feedback |
| Edit modal | Single textarea con respuesta propuesta | Slack modal with input block |
| Error display | Ephemeral message con error y retry option | Non-blocking |

### Message Template (Block Kit)

```json
{
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "📧 Email Action Required"}
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "*From:* john@client.com\n*Subject:* Contract renewal question"}
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "*Classification:* URGENT (75% confidence)"}
    },
    {
      "type": "divider"
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "*📝 Proposed Response:*\n```Hi John, Thanks for reaching out...```"}
    },
    {
      "type": "actions",
      "elements": [
        {"type": "button", "text": {"type": "plain_text", "text": "✅ Approve"}, "style": "primary", "action_id": "approve_action"},
        {"type": "button", "text": {"type": "plain_text", "text": "✏️ Edit"}, "action_id": "edit_action"},
        {"type": "button", "text": {"type": "plain_text", "text": "⏰ Snooze"}, "action_id": "snooze_action"},
        {"type": "button", "text": {"type": "plain_text", "text": "❌ Reject"}, "style": "danger", "action_id": "reject_action"}
      ]
    }
  ]
}
```

---

## Security Considerations

- [x] ¿Requiere autenticación? **Sí** - OAuth 2.0 con Slack
- [x] ¿Qué datos son sensibles? **Bot tokens, access tokens** - encrypted at rest
- [x] ¿Necesita rate limiting? **Sí** - Slack tiene límites, respetarlos
- [x] ¿Cumple con GDPR/privacidad? **Sí** - datos de Slack son del usuario, puede desconectar
- [x] Token rotation: Access tokens se refrescan automáticamente
- [x] Scope mínimo: Solo permisos necesarios (chat:write, users:read)

---

## Open Questions

- [x] ¿Workspace único o múltiples? → **MVP: 1 workspace por usuario**
- [x] ¿Permitir elegir canal o solo DM? → **MVP: Solo DM con el bot**
- [x] ¿Timeout para acciones? → **24h, después se marca como expirado**

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/integrations/slack/install` | Redirect a Slack OAuth |
| GET | `/api/v1/integrations/slack/callback` | OAuth callback handler |
| POST | `/api/v1/webhooks/slack/events` | Slack events webhook |
| POST | `/api/v1/webhooks/slack/interactive` | Interactive components callback |
| GET | `/api/v1/integrations/slack/status` | Check connection status |
| DELETE | `/api/v1/integrations/slack` | Disconnect Slack |

---

## Data Model

### slack_installations

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK to users table |
| team_id | VARCHAR | Slack workspace ID |
| team_name | VARCHAR | Slack workspace name |
| bot_user_id | VARCHAR | Bot user ID in workspace |
| bot_access_token | VARCHAR (encrypted) | Bot OAuth token |
| user_access_token | VARCHAR (encrypted) | User OAuth token (optional) |
| dm_channel_id | VARCHAR | DM channel with user |
| scopes | TEXT | Comma-separated scopes |
| installed_at | TIMESTAMP | Installation timestamp |
| updated_at | TIMESTAMP | Last token refresh |
| is_active | BOOLEAN | Connection status |

---

## Interview Log

### Session 1 - 2026-01-31

- Discutido: Core requirements for Slack integration
- Decisiones:
  - Slack Bolt for Python as framework
  - Socket Mode for development (no public URL needed)
  - Block Kit for rich messages
  - DM-only for MVP (no channels)
- Pendiente: None - spec complete

---

*Status: ✅ Interview Complete*
*Created: 2026-01-31*
*Last updated: 2026-01-31*
