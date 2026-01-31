# FounderPilot - Features Dashboard

## Overview

Suite de 3 agentes autónomos para founders: InboxPilot, InvoicePilot, MeetingPilot.

---

## MVP Scope

**Target:** 6-8 semanas
**Total Features:** 8
**Progress:** 0%

---

## Features

### Platform Core

| ID | Feature | Status | Phase | Progress | Priority | Updated |
|----|---------|--------|-------|----------|----------|---------|
| [FEAT-001](./FEAT-001-auth-onboarding/) | Auth & Onboarding | ⚪ Pending | - | - | P0 | 2026-01-31 |
| [FEAT-002](./FEAT-002-billing-plans/) | Billing & Plans | 🟡 In Progress | Implement | 0/30 | P0 | 2026-01-31 |
| [FEAT-006](./FEAT-006-slack-integration/) | Slack Integration | ⚪ Pending | - | - | P0 | 2026-01-31 |
| [FEAT-007](./FEAT-007-audit-dashboard/) | Audit Dashboard | ⚪ Pending | - | - | P0 | 2026-01-31 |
| [FEAT-008](./FEAT-008-usage-tracking/) | Usage Tracking | ⚪ Pending | - | - | P1 | 2026-01-31 |

### Agentes

| ID | Agente | Status | Phase | Progress | Priority | Updated |
|----|--------|--------|-------|----------|----------|---------|
| [FEAT-003](./FEAT-003-inbox-pilot/) | InboxPilot | ⚪ Pending | - | - | P0 | 2026-01-31 |
| [FEAT-004](./FEAT-004-invoice-pilot/) | InvoicePilot | ⚪ Pending | - | - | P0 | 2026-01-31 |
| [FEAT-005](./FEAT-005-meeting-pilot/) | MeetingPilot | ⚪ Pending | - | - | P0 | 2026-01-31 |

---

## Dependencies Graph

```
              ┌───────────┐
              │  FEAT-001 │  Auth & Onboarding
              │    (P0)   │  Google OAuth + Gmail + Slack
              └─────┬─────┘
                    │
          ┌─────────┼─────────┬─────────────────┐
          ▼         ▼         ▼                 ▼
    ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
    │  FEAT-002 │ │  FEAT-006 │ │  FEAT-003 │ │  FEAT-005 │
    │  Billing  │ │   Slack   │ │InboxPilot │ │MeetingPil │
    └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └───────────┘
          │             │             │
          ▼             │             ▼
    ┌───────────┐       │       ┌───────────┐
    │  FEAT-008 │       │       │  FEAT-004 │
    │  Usage    │       │       │InvoicePil │
    └───────────┘       │       └─────┬─────┘
                        │             │
                        └──────┬──────┘
                               ▼
                         ┌───────────┐
                         │  FEAT-007 │
                         │  Audit    │
                         └───────────┘
```

---

## Implementation Order

### Semana 1-2: Foundation
| Order | Feature | Descripción |
|-------|---------|-------------|
| 1 | FEAT-001 | Auth & Onboarding - Base de todo |
| 2 | FEAT-006 | Slack Integration - Canal de comunicación |
| 3 | FEAT-002 | Billing & Plans - Monetización ready |

### Semana 3-4: Core Agents
| Order | Feature | Descripción |
|-------|---------|-------------|
| 4 | FEAT-003 | InboxPilot - Agente principal |
| 5 | FEAT-005 | MeetingPilot - Segundo agente |

### Semana 5-6: Complete Suite
| Order | Feature | Descripción |
|-------|---------|-------------|
| 6 | FEAT-004 | InvoicePilot - Tercer agente |
| 7 | FEAT-007 | Audit Dashboard - Transparencia |
| 8 | FEAT-008 | Usage Tracking - Control de uso |

### Semana 7-8: Polish & Launch
- Integration testing
- Bug fixes
- Landing page
- Beta launch

---

## Feature Summaries

| Feature | User Value |
|---------|------------|
| **FEAT-001** | "Conectar cuentas en 2 minutos" |
| **FEAT-002** | "Elige tu plan, paga con Stripe" |
| **FEAT-003** | "El agente lee mi inbox y prepara respuestas" |
| **FEAT-004** | "Nunca olvido cobrar una factura" |
| **FEAT-005** | "Llego a calls con contexto" |
| **FEAT-006** | "Controlo todo desde Slack" |
| **FEAT-007** | "Sé exactamente qué hizo el agente" |
| **FEAT-008** | "Control de mi consumo" |

---

## Status Legend

| Symbol | Status | Description |
|--------|--------|-------------|
| ⚪ | Pending | Not started - Ready for development |
| 🟡 | In Progress | Active development |
| 🔵 | In Review | PR created, awaiting review |
| 🟢 | Complete | Merged and wrapped up |
| 🔴 | Blocked | Needs attention |

## Priority Legend

| Priority | Description |
|----------|-------------|
| P0 | Critical - MVP blocker |
| P1 | High - MVP nice-to-have |
| P2 | Medium - Post-MVP |
| P3 | Low - Future |

---

## Quick Stats

```
MVP Progress:    [░░░░░░░░░░░░░░░░░░░░] 0%
P0 Features:     0/7 complete
P1 Features:     0/1 complete
```

---

## Post-MVP (v1.1+)

| Feature | Priority | Notes |
|---------|----------|-------|
| Outlook integration | P1 | After Gmail proven |
| Weekly Digest email | P1 | Scheduled summary |
| VIP contacts | P2 | Priority routing |
| Team features | P2 | Multi-user accounts |
| Notion integration | P2 | Knowledge base |
| Agent Builder SDK | P3 | Framework for builders |

---

## Out of Scope (Won't Have v1)

- Mobile app
- Voice agents
- Enterprise SSO/SAML
- On-premise deployment

---

## How to Use

### Start Development
```bash
# Interview a feature
/interview FEAT-001

# Or run autonomous development
/ralph feature FEAT-001
```

### Manual Cycle
1. `/interview FEAT-XXX` - Define spec
2. `/plan FEAT-XXX` - Create design
3. Create branch, implement, PR, merge
4. `/wrap-up FEAT-XXX` - Close feature

---

## Links

- [Project Definition](../project.md)
- [Architecture](../architecture/_index.md)
- [Story Mapping](../discovery/story-mapping-founderops.md)
- [Feature Template](./_template/)
- [Feature Cycle](../feature_cycle.md)

---

*Last updated: 2026-01-31*
*Next step: `/interview FEAT-001`*
