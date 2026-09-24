# ADR-005: JWT + OAuth2 para Autenticación

## Status
Accepted

## Date
2026-01-31

## Context
FounderPilot necesita autenticar usuarios que:
- Ya tienen cuenta Google (usan Gmail)
- Acceden desde web dashboard
- Interactúan via Slack bot
- Pueden tener múltiples workspaces/equipos

## Options Considered

### Option 1: JWT + OAuth2 (Google)
**Pros:**
- Stateless (escala fácil)
- Google OAuth = zero friction (ya tienen Gmail)
- Estándar de la industria
- Fácil integración con FastAPI

**Cons:**
- Necesita refresh token flow
- JWT revocation requiere blacklist

### Option 2: Session-based
**Pros:**
- Simple de implementar
- Revocation instantánea

**Cons:**
- Stateful (necesita session store)
- No escala horizontalmente fácil
- Más complejo para APIs

### Option 3: API Keys only
**Pros:**
- Muy simple
- Bueno para developers

**Cons:**
- No apto para usuarios finales
- Sin refresh/revoke granular

## Decision
**JWT + OAuth2 con Google** - Los usuarios ya tienen Gmail, zero friction. JWT permite escalar stateless.

## Consequences
- Google OAuth2 para signup/login
- JWT con 24h expiry + refresh tokens
- Slack OAuth separado para bot integration
- Roles: user, admin (futuro: team member)
- Blacklist en Redis para token revocation

## References
- [FastAPI OAuth2](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Google OAuth2](https://developers.google.com/identity/protocols/oauth2)
