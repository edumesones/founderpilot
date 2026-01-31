# ADR-006: Next.js + Slack Bot para Frontend

## Status
Accepted

## Date
2026-01-31

## Context
FounderPilot necesita interfaces para:
- Dashboard web: ver audit logs, configurar agentes, aprobar acciones
- Notificaciones real-time: escalations, alertas
- Interacción rápida: aprobar/rechazar desde móvil

## Options Considered

### Option 1: Next.js + Slack Bot
**Pros:**
- Next.js: SSR, SEO, Vercel deploy fácil
- Slack: donde ya están los founders
- Push notifications via Slack
- Approve/reject con botones de Slack
- React ecosystem maduro

**Cons:**
- Dos interfaces que mantener
- Slack API tiene rate limits

### Option 2: Gradio/Streamlit
**Pros:**
- Rápido para prototipos
- Python-native

**Cons:**
- No production-ready para SaaS
- UI limitada
- Sin mobile-friendly

### Option 3: Solo API + Slack
**Pros:**
- Mínimo desarrollo
- Todo en Slack

**Cons:**
- Sin dashboard visual
- Audit logs difíciles de explorar
- Limita funcionalidad futura

## Decision
**Next.js para dashboard + Slack bot para notificaciones/actions**

El dashboard es para configuración y audit logs. Slack es para real-time actions (aprobar, escalar).

## Consequences
- Next.js 14 con App Router
- Tailwind CSS + shadcn/ui
- Slack Bolt SDK para el bot
- WebSockets para real-time updates en dashboard
- Slack para notificaciones push y quick actions

## References
- [Next.js docs](https://nextjs.org/docs)
- [Slack Bolt Python](https://slack.dev/bolt-python/)
- [shadcn/ui](https://ui.shadcn.com/)
