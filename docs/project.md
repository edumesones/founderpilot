# Project: FounderPilot

## Vision

**One-liner:** Suite de agentes autónomos especializados para founders - InboxPilot, InvoicePilot, MeetingPilot.

**Problem:**
- Founders/solopreneurs están abrumados "wearing all the hats"
- Las herramientas de automatización actuales son todo-o-nada (o full manual o black box)
- Los agentes de IA actuales requieren "babysitting" constante
- Over-automation mata la confianza con clientes/usuarios

**Solution:**
3 agentes especializados que automatizan lo repetitivo PERO:
- Mantienen al founder en control (human-on-the-loop)
- Escalan inteligentemente cuando hay incertidumbre
- Son 100% transparentes y auditables
- Construyen confianza en lugar de destruirla

**Success criteria:**
- 50 founders en trial en 60 días
- 20 clientes pagando en 90 días
- $1,000 MRR en 120 días

---

## Producto: 3 Agentes Especializados

| Agente | Pain Point que resuelve | Core Value |
|--------|-------------------------|------------|
| **InboxPilot** | "Paso 2h/día en email" | Clasifica, prioriza, draftea respuestas |
| **InvoicePilot** | "Olvido cobrar facturas" | Detecta, trackea, envía reminders |
| **MeetingPilot** | "Llego a calls sin contexto" | Prep pre-call, notas, follow-up |

---

## Business Model

### Arquitectura: Multi-tenant SaaS

```
┌─────────────────────────────────────────────────────────────────┐
│                    TU INFRAESTRUCTURA (AWS)                     │
│                                                                 │
│   Customer A ──┐                                                │
│   Customer B ──┼──▶ [Un solo deployment] ◀── Datos aislados    │
│   Customer C ──┘         │                    por tenant_id     │
│                          ▼                                      │
│              PostgreSQL + Redis + Workers                       │
│                                                                 │
│   Costo fijo: ~$150-200/mes (escala con clientes)              │
└─────────────────────────────────────────────────────────────────┘
```

### Pricing: Agent-Based

| Plan | Precio | Incluye | Target |
|------|--------|---------|--------|
| **InboxPilot** | $29/mes | 500 emails/mes | Solo email |
| **InvoicePilot** | $19/mes | 50 invoices/mes | Solo cobros |
| **MeetingPilot** | $19/mes | 30 meetings/mes | Solo meetings |
| **Bundle** | $49/mes | Los 3 agentes | Best value |

**Overage:** $0.02/email, $0.10/invoice, $0.15/meeting extra

### Unit Economics

| Concepto | Por cliente/mes |
|----------|-----------------|
| LLM costs | ~$2-5 |
| Infra (prorrateado) | ~$1-2 |
| Stripe fees (3%) | ~$1.50 |
| **Costo total** | **~$5-8** |
| **Precio Bundle** | **$49** |
| **Margen bruto** | **~85%** |

### Customer Journey

```
1. Signup      → Google OAuth (gratis)
2. Onboarding  → Conecta Gmail + Slack
3. Trial       → 14 días con todos los agentes
4. Conversion  → Elige plan (1 agente o bundle)
5. Usage       → Dashboard muestra consumo
6. Billing     → Stripe cobra mensualmente
```

---

## Users

**Primary:** Founders de startups y solopreneurs (1-10 personas)
- Técnicamente competentes pero sin tiempo
- Ya usan Notion, Slack, email, calendarios
- Frustrados con VAs (training, turnover) y herramientas fragmentadas
- Dispuestos a pagar $30-50/mes por recuperar tiempo

**Technical level:** Intermediate (saben usar APIs pero no quieren codear)

---

## Core Features (MVP)

### Platform Core
| ID | Feature | Descripción |
|----|---------|-------------|
| FEAT-001 | Auth & Onboarding | Google OAuth, Gmail connect, Slack connect |
| FEAT-002 | Billing & Plans | Stripe, planes, usage tracking, trials |
| FEAT-006 | Slack Integration | Notificaciones, actions, escalation |
| FEAT-007 | Audit Dashboard | Ver acciones, confidence, historial |
| FEAT-008 | Usage Tracking | Límites, overage, dashboard de uso |

### Agentes
| ID | Agente | Descripción |
|----|--------|-------------|
| FEAT-003 | InboxPilot | Fetch, classify, draft, escalate emails |
| FEAT-004 | InvoicePilot | Detect invoices, track, send reminders |
| FEAT-005 | MeetingPilot | Pre-call prep, context summary, follow-up |

---

## Technical Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Language | Python 3.11 | Ecosistema IA maduro, LangGraph |
| Agent Framework | LangGraph | Control granular, human-in-loop nativo |
| Backend API | FastAPI | Async, auto-docs, Pydantic |
| Database | PostgreSQL | Multi-tenant, ACID, audit trail |
| Queue | Redis + Celery | Workflows async, scheduled tasks |
| Auth | JWT + Google OAuth | Stateless, zero friction |
| Frontend | Next.js 14 | Dashboard + landing page |
| Notifications | Slack Bot (Bolt) | Actions inline, escalation |
| LLM | Claude + GPT-4o | Multi-provider, cost optimization |
| Observability | Langfuse + CloudWatch | LLM traces + infra monitoring |
| Payments | Stripe | Subscriptions, usage billing |
| Hosting | Docker + AWS ECS | Containers, escalable |

---

## Architecture Principles

1. **Multi-tenant** - Un deployment, datos aislados por tenant_id
2. **Human-on-the-loop** - Agente propone, humano aprueba (acciones críticas)
3. **Escalation-first** - Si confianza < 80%, escalar a Slack
4. **Audit everything** - Log inmutable de cada acción
5. **Usage-based** - Track tokens, emails, invoices por tenant
6. **Fail gracefully** - Retry con backoff, circuit breaker

---

## Integrations v1

| Integration | Purpose | Priority | Agente |
|-------------|---------|----------|--------|
| Gmail API | Inbox triage, send drafts | P0 | InboxPilot |
| Slack API | Notifications, actions | P0 | Core |
| Google Calendar | Meeting detection, prep | P0 | MeetingPilot |
| Stripe | Billing, subscriptions | P0 | Core |
| Stripe/Invoice tools | Invoice detection | P1 | InvoicePilot |

---

## Constraints

- **Timeline:** MVP en 6-8 semanas
- **Budget:** Bootstrap (APIs pay-as-you-go)
- **Team:** Solo founder + Claude como copilot
- **Compliance:** GDPR-aware (datos de email)

---

## Out of Scope (v1)

- Mobile app
- Voice agents
- Enterprise SSO/SAML
- On-premise deployment
- Agent Builder/Framework (v2)
- Outlook integration (v1.1)
- Notion integration (v1.1)

---

## Risks & Unknowns

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM costs escalan | High | Límites por plan, cache agresivo |
| Gmail OAuth approval | High | Empezar con limited users, apply for verification |
| Founders no confían | High | Audit logs visibles, easy rollback |
| Competencia (Lindy) | Medium | Pricing accesible, nicho específico |

---

## Research Insights (Reddit - Enero 2026)

### Thread más relevante (275pts, 143cmt):
> "We automated everything and now nobody trusts anything"
> - r/Entrepreneur

**Key quotes:**
- "Trust is the only currency small builders have"
- "Agent handles this now. Tracks what's due, sends reminders, escalates to me only if needed"
- "Don't automate everything - automate the heavy lifting, repetitive part"

### Implicaciones:
1. Vender "control + automatización", no "automatización total"
2. Escalation visible es feature, no bug
3. Audit trail como diferenciador

---

## Open Questions

- [x] ¿Nombre final? → **FounderPilot**
- [x] ¿Freemium o trial? → **14 días trial, luego pago**
- [x] ¿Priorizar Gmail o Outlook? → **Gmail primero**
- [x] ¿Modelo de negocio? → **Agent-based pricing, bundle $49**
- [ ] ¿Cómo detectar invoices? (regex, LLM, Stripe?)
- [ ] ¿Integrar con calendarios externos o solo Google?

---

*Project definition completed: 2026-01-31*
*Status: Ready for implementation*
