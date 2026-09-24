---
name: architecture-designer
description: Define technical architecture and create ADRs. Triggers on "Help me define the architecture", "Define architecture", "Let's design the architecture".
globs: ["docs/architecture/**", "docs/decisions/**", "docs/project.md"]
---

# Architecture Designer (Fase 0)

Transform project requirements into concrete architectural decisions with proper ADR documentation.

## Triggers

- "Help me define the architecture"
- "Define architecture"
- "Let's design the architecture"
- "Help me with technical architecture"
- `/architecture`

## Prerequisites

- `docs/project.md` should exist with project definition
- If not exists, suggest: "Let's first interview about the project"

## Purpose

Create:
1. **Architecture overview** in `docs/architecture/_index.md`
2. **ADRs** (Architecture Decision Records) in `docs/decisions/`
3. **Technical foundation** for feature development

## Process

### 1. Read Project Context

```bash
# Read project definition
cat docs/project.md

# Check existing architecture docs
ls -la docs/architecture/ 2>/dev/null
ls -la docs/decisions/ 2>/dev/null
```

### 2. Identify Key Decisions

Based on project.md, identify decisions needed:

| Category | Typical Decisions |
|----------|-------------------|
| **Language/Runtime** | Python, Node, Go, Rust |
| **Framework** | FastAPI, Django, Express, Next.js |
| **Database** | PostgreSQL, MongoDB, SQLite, Redis |
| **Authentication** | JWT, OAuth, Session, API Keys |
| **Hosting** | AWS, GCP, Azure, Vercel, Self-hosted |
| **API Style** | REST, GraphQL, gRPC |
| **Frontend** | React, Vue, Gradio, CLI |
| **Caching** | Redis, Memcached, In-memory |
| **Queue/Async** | Celery, RQ, SQS, None |
| **Monitoring** | CloudWatch, Datadog, Prometheus |

### 3. Interview for Each Decision

For each major decision, ask:

```
"For [CATEGORY], I see a few options:

A) [Option A] - [Pros: X, Y] [Cons: Z]
B) [Option B] - [Pros: X, Y] [Cons: Z]
C) [Option C] - [Pros: X, Y] [Cons: Z]

Based on your project (MVP timeline, team size, scale needs), 
I'd recommend [X] because [reason].

What's your preference?"
```

### 4. Create ADRs

For each decision, create `docs/decisions/ADR-NNN-title.md`:

```markdown
# ADR-001: Use FastAPI for Backend Framework

## Status
Accepted

## Date
{date}

## Context
We need a backend framework for [project]. Requirements:
- REST API endpoints
- Async support for external API calls
- Auto-generated OpenAPI docs
- Python ecosystem (team expertise)

## Options Considered

### Option 1: FastAPI
**Pros:**
- Native async support
- Automatic OpenAPI/Swagger docs
- Pydantic validation built-in
- High performance

**Cons:**
- Smaller ecosystem than Django
- Less batteries-included

### Option 2: Django + DRF
**Pros:**
- Batteries included (admin, ORM, auth)
- Large ecosystem
- Mature and stable

**Cons:**
- Sync by default (async is bolted on)
- Heavier for simple APIs

### Option 3: Flask
**Pros:**
- Simple and flexible
- Large ecosystem

**Cons:**
- No built-in validation
- Manual OpenAPI setup
- Sync only

## Decision
**FastAPI** - Best fit for async API with auto-documentation needs.

## Consequences
- Team needs FastAPI familiarity (minor learning curve)
- Will use SQLAlchemy for ORM (not Django ORM)
- Pydantic models for all request/response validation

## References
- [FastAPI docs](https://fastapi.tiangolo.com/)
```

### 5. Create Architecture Overview

Update `docs/architecture/_index.md`:

```markdown
# Architecture Overview

## System Context

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Backend   │────▶│  Database   │
│  (Browser)  │     │  (FastAPI)  │     │ (PostgreSQL)│
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  External   │
                    │    APIs     │
                    └─────────────┘
```

## Tech Stack

| Layer | Technology | ADR |
|-------|------------|-----|
| Backend | FastAPI + Python 3.11 | [ADR-001](../decisions/ADR-001-fastapi.md) |
| Database | PostgreSQL 15 | [ADR-002](../decisions/ADR-002-postgresql.md) |
| Auth | JWT + OAuth2 | [ADR-003](../decisions/ADR-003-auth.md) |
| Hosting | AWS ECS | [ADR-004](../decisions/ADR-004-hosting.md) |

## Project Structure

```
src/
├── api/              # FastAPI routes
│   ├── __init__.py
│   ├── routes/
│   └── dependencies.py
├── models/           # SQLAlchemy models
├── services/         # Business logic
├── schemas/          # Pydantic schemas
└── utils/            # Helpers

tests/
├── unit/
├── integration/
└── conftest.py
```

## Key Patterns

- **Repository pattern** for data access
- **Service layer** for business logic
- **Dependency injection** via FastAPI
- **Pydantic** for all validation

## Non-Functional Requirements

| Aspect | Target | Notes |
|--------|--------|-------|
| Response time | <200ms p95 | For API endpoints |
| Availability | 99.5% | MVP target |
| Data retention | 1 year | Compliance requirement |

## Security

- JWT tokens with 24h expiry
- HTTPS only
- Input validation on all endpoints
- SQL injection prevention via ORM

---
*Last updated: {date}*
*ADRs: [View all](../decisions/)*
```

### 6. Interview Rules

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  ARCHITECTURE INTERVIEW RULES                                                  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  1. Always provide options with trade-offs                                    ║
║     Never ask "what database?" - ask "PostgreSQL or MongoDB? Here's why..."  ║
║                                                                                ║
║  2. Make recommendations based on project context                             ║
║     "Given your MVP timeline, I recommend X"                                  ║
║                                                                                ║
║  3. Create ADR immediately after each decision                                ║
║     Don't wait until the end                                                  ║
║                                                                                ║
║  4. Challenge over-engineering                                                 ║
║     "Do you really need Kubernetes for MVP? ECS is simpler."                 ║
║                                                                                ║
║  5. Document the WHY, not just the WHAT                                       ║
║     Future you will thank present you                                         ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 7. Completion Check

Before ending, verify:
- [ ] All major categories have decisions
- [ ] Each decision has an ADR
- [ ] Architecture overview exists
- [ ] Project structure is defined
- [ ] No conflicting decisions

### 8. Handoff

When complete:

```
✅ Architecture defined. Created:
- docs/architecture/_index.md (overview)
- docs/decisions/ADR-001-*.md through ADR-00N-*.md

Next step:
"Define MVP features" → Creates feature folders ready for implementation

Or: "Let's start with the first feature"
```

## Example Flow

```
User: "Help me define the architecture"

Claude: [Reads docs/project.md]

"Based on your project (CLI dotfiles manager, cross-platform, single developer):

Let's start with the core decisions:

**Language/Runtime:**
A) Python - You know it, great CLI libs (Click, Typer), cross-platform
B) Go - Single binary distribution, fast, but learning curve
C) Rust - Performance, but overkill for this use case

For a dotfiles CLI with your Python background, I'd recommend **Python + Typer**.
Fast to build, easy to maintain, pip installable.

Your preference?"

User: "Python + Typer sounds good"

Claude: [Creates ADR-001-python-typer.md]

"✅ ADR-001 created. Next decision:

**Configuration Storage:**
A) YAML files - Human readable, familiar
B) TOML - Python-native (tomllib), cleaner syntax
C) JSON - Universal, but verbose

For a developer tool, **TOML** is idiomatic and Python 3.11 has built-in support.

Your preference?"

[continues...]
```
