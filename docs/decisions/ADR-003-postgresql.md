# ADR-003: PostgreSQL para Database

## Status
Accepted

## Date
2026-01-31

## Context
FounderPilot necesita almacenar:
- Audit logs inmutables (cada acción del agente)
- Estado de workflows (checkpoints de LangGraph)
- Datos de usuarios y configuraciones
- Historial de emails, invoices, etc.

Requisitos:
- ACID compliance (audit trail crítico)
- Queries complejas (reportes, analytics)
- JSON support (datos semi-estructurados de LLMs)
- Escala a millones de registros

## Options Considered

### Option 1: PostgreSQL
**Pros:**
- ACID compliant
- JSONB para datos flexibles
- Excelente para queries complejas
- Mature, battle-tested
- AWS RDS disponible

**Cons:**
- Más setup que SQLite
- Requiere hosting

### Option 2: MongoDB
**Pros:**
- Schema flexible
- Fácil para documentos

**Cons:**
- No ACID por defecto
- Queries complejas más difíciles
- Overkill para nuestro caso

### Option 3: SQLite
**Pros:**
- Zero config
- Embedded

**Cons:**
- No escala horizontalmente
- Sin concurrent writes
- No production-ready para SaaS

## Decision
**PostgreSQL** - ACID es innegociable para audit trail. JSONB nos da flexibilidad para datos de LLM.

## Consequences
- Usaremos SQLAlchemy async como ORM
- Alembic para migraciones
- AWS RDS PostgreSQL en producción
- Docker PostgreSQL en desarrollo

## References
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [SQLAlchemy async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
