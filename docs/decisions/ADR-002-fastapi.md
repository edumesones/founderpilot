# ADR-002: FastAPI para Backend API

## Status
Accepted

## Date
2026-01-31

## Context
Necesitamos un framework web Python para:
- Exponer APIs REST para el dashboard
- Manejar webhooks de Gmail, Slack, etc.
- Ejecutar llamadas async a LLMs y servicios externos
- Auto-documentar endpoints para el framework de builders

## Options Considered

### Option 1: FastAPI
**Pros:**
- Async nativo (crítico para LLM calls)
- OpenAPI/Swagger automático
- Pydantic validation integrado
- Alto performance (Starlette + uvicorn)
- Type hints = mejor DX

**Cons:**
- Sin admin panel incluido
- Menos "batteries included" que Django

### Option 2: Django + DRF
**Pros:**
- Admin panel gratis
- ORM maduro
- Ecosystem enorme

**Cons:**
- Sync por defecto (async es add-on)
- Más pesado para APIs puras
- Overkill para nuestro caso

### Option 3: Flask
**Pros:**
- Simple y flexible
- Familiar

**Cons:**
- Sin validación nativa
- Sin async
- Manual OpenAPI setup

## Decision
**FastAPI** - Async es crítico para llamadas a LLMs (pueden tomar 5-30s). Auto-documentación ayuda al framework para builders.

## Consequences
- Usaremos Pydantic para todos los schemas
- SQLAlchemy async para database
- uvicorn como server ASGI
- OpenAPI spec disponible automáticamente en /docs

## References
- [FastAPI docs](https://fastapi.tiangolo.com/)
