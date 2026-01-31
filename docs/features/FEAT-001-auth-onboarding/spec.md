# FEAT-001: Auth & Onboarding

## Summary
Sistema de autenticacion y onboarding que permite a founders registrarse con Google OAuth, conectar su cuenta de Gmail para que el agente lea/envie emails, y conectar Slack para recibir notificaciones y aprobar acciones. Base fundamental de FounderPilot - sin auth no hay producto.

---

## User Stories

- [x] Como **founder** quiero **registrarme con mi cuenta de Google** para **no crear otra password y empezar rapido**
- [x] Como **founder** quiero **conectar mi Gmail** para **que el agente pueda leer y responder emails por mi**
- [x] Como **founder** quiero **conectar Slack** para **recibir notificaciones y aprobar acciones del agente**
- [x] Como **founder** quiero **ver un resumen de mis conexiones** para **saber que todo esta configurado**
- [x] Como **founder** quiero **desconectar una integracion** para **revocar permisos si lo necesito**

---

## Acceptance Criteria

- [x] Usuario puede hacer signup/login con Google OAuth en menos de 30 segundos
- [x] Despues de login, se redirige a pantalla de onboarding si es primera vez
- [x] Usuario puede conectar Gmail con scopes: read, send, labels
- [x] Usuario puede conectar Slack (instalar bot en workspace)
- [x] Tokens de Gmail y Slack se almacenan encriptados
- [x] JWT de sesion con 24h expiry + refresh token
- [x] Endpoint para verificar estado de conexiones
- [x] Endpoint para revocar/desconectar cada integracion
- [x] Audit log registra: signup, login, connect, disconnect

---

## Technical Decisions

| # | Area | Pregunta | Decision | Notas |
|---|------|----------|----------|-------|
| 1 | Auth | Metodo de autenticacion? | Google OAuth2 | Zero friction, ya tienen Gmail |
| 2 | Tokens | Como manejar sesiones? | JWT 24h + refresh tokens | Stateless, escala bien |
| 3 | Storage | Donde guardar OAuth tokens? | PostgreSQL encriptados (Fernet) | AES-256 encryption |
| 4 | Revocation | Como invalidar tokens? | Redis blacklist | TTL = token expiry |
| 5 | Gmail | Que scopes pedir? | gmail.readonly, gmail.send, gmail.labels | Minimo necesario |
| 6 | Slack | Tipo de app? | Bot token + OAuth | Bot para DMs, OAuth para identity |
| 7 | Onboarding | Flujo obligatorio? | Si, 3 pasos secuenciales | Google -> Gmail -> Slack |
| 8 | Frontend | Donde vive el onboarding? | Next.js pages | /auth/*, /onboarding/* |

---

## Scope

### In Scope (MVP)

- Google OAuth2 signup/login
- JWT session management con refresh tokens
- Gmail OAuth2 connection (read, send, labels)
- Slack OAuth2 + Bot installation
- Onboarding flow de 3 pasos
- Estado de conexiones (API + UI)
- Desconectar integraciones
- Audit log de eventos de auth

### Out of Scope

- Microsoft/Outlook OAuth (ver FEAT-xxx futuro)
- Email/password signup
- Multi-factor authentication (2FA)
- Team invitations (ver Release 3)
- SSO/SAML enterprise (Won't Have v1)
- Password reset (no aplica, solo OAuth)

---

## Dependencies

### Requires (this feature needs)

- [x] ADR-002 - FastAPI como backend
- [x] ADR-003 - PostgreSQL para storage
- [x] ADR-004 - Redis para token blacklist
- [x] ADR-005 - JWT + OAuth2 decision
- [x] ADR-006 - Next.js frontend

### Blocks (features that need this)

- FEAT-002 - Billing & Plans (necesita user)
- FEAT-003 - InboxPilot (necesita Gmail connection)
- FEAT-004 - InvoicePilot (necesita Gmail)
- FEAT-005 - MeetingPilot (necesita Calendar)
- FEAT-006 - Slack Integration (necesita Slack OAuth)
- FEAT-007 - Audit Dashboard (necesita user context)
- FEAT-008 - Usage Tracking (necesita user)

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| User cancela OAuth flow | Mostrar error amigable, boton "Reintentar" |
| Token de Gmail expirado | Usar refresh token automaticamente |
| Refresh token expirado | Pedir re-autorizacion via UI |
| Usuario revoca permisos en Google | Detectar error 401, marcar como "Necesita reconectar" |
| Slack bot removido del workspace | Detectar error, notificar en dashboard |
| Network error durante OAuth | Retry con backoff, mostrar error si falla |
| Usuario ya existe (mismo email) | Login en vez de signup, merge data |
| Scopes insuficientes | Mostrar que scopes faltan, pedir re-auth |

---

## UI/UX Decisions

| Elemento | Decision | Referencia |
|----------|----------|------------|
| Login page | Unico boton "Continue with Google" | Minimalista, zero friction |
| Onboarding | Stepper de 3 pasos | Google done -> Gmail -> Slack |
| Success state | Checkmarks verdes animados | Feedback visual positivo |
| Error state | Mensaje claro + "Try again" | Sin jerga tecnica |
| Dashboard connections | Cards con status on/off | Toggle para desconectar |
| Loading | Skeleton + spinner durante OAuth | Usuario sabe que algo pasa |

---

## Security Considerations

- [x] HTTPS obligatorio en todos los endpoints
- [x] OAuth tokens encriptados en DB (Fernet/AES-256)
- [x] JWT firmados con RS256 (asymmetric)
- [x] PKCE flow para OAuth2 (prevent interception)
- [x] State parameter para CSRF protection
- [x] Refresh tokens rotados en cada uso
- [x] Rate limiting en /auth/* endpoints (10/min)
- [x] No exponer tokens en logs ni URLs
- [x] Audit log inmutable para compliance

---

## API Endpoints

### Auth

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/auth/google` | Iniciar Google OAuth flow | No |
| GET | `/api/v1/auth/google/callback` | Google OAuth callback | No |
| POST | `/api/v1/auth/refresh` | Refresh JWT token | Refresh token |
| POST | `/api/v1/auth/logout` | Logout (blacklist token) | JWT |
| GET | `/api/v1/auth/me` | Get current user info | JWT |

### Integrations

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/integrations/gmail/connect` | Iniciar Gmail OAuth | JWT |
| GET | `/api/v1/integrations/gmail/callback` | Gmail OAuth callback | JWT |
| DELETE | `/api/v1/integrations/gmail` | Disconnect Gmail | JWT |
| GET | `/api/v1/integrations/slack/connect` | Iniciar Slack OAuth | JWT |
| GET | `/api/v1/integrations/slack/callback` | Slack OAuth callback | JWT |
| DELETE | `/api/v1/integrations/slack` | Disconnect Slack | JWT |
| GET | `/api/v1/integrations/status` | Get all integration status | JWT |

### Onboarding

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/onboarding/status` | Get onboarding progress | JWT |
| POST | `/api/v1/onboarding/complete` | Mark onboarding as done | JWT |

---

## Data Model

### User
```python
class User:
    id: UUID
    email: str  # unique, from Google
    name: str
    picture_url: Optional[str]
    google_id: str  # unique, from Google
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime
```

### Integration
```python
class Integration:
    id: UUID
    user_id: UUID  # FK to User
    provider: str  # "gmail", "slack"
    access_token_encrypted: str
    refresh_token_encrypted: str
    token_expires_at: datetime
    scopes: List[str]
    metadata: dict  # provider-specific (workspace_id, etc)
    status: str  # "active", "expired", "revoked"
    connected_at: datetime
    updated_at: datetime
```

### RefreshToken
```python
class RefreshToken:
    id: UUID
    user_id: UUID  # FK to User
    token_hash: str  # hashed, not raw
    expires_at: datetime
    created_at: datetime
    revoked_at: Optional[datetime]
```

---

## Open Questions

- [x] Que hacer si el usuario tiene multiples workspaces de Slack? **Decision: Permitir solo 1 por ahora, UI para elegir cual**
- [x] Guardar historial de tokens o solo el actual? **Decision: Solo actual, audit log para historial**
- [x] Limite de intentos de login fallidos? **Decision: Rate limit general es suficiente para MVP**

---

## Interview Log

### Session 1 - 2026-01-31 (Ralph Loop)
- Spec generada automaticamente basada en:
  - ADR-005 (JWT + OAuth2)
  - Architecture doc
  - Story mapping (MVP flow)
- Decisiones alineadas con arquitectura existente
- No hay TBD - spec completa

---

*Status: Interview Complete*
*Created: 2026-01-31*
*Last updated: 2026-01-31*
