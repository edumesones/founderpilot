# ADR-004: Redis + Celery para Queue/Async

## Status
Accepted

## Date
2026-01-31

## Context
Los agentes de FounderPilot ejecutan workflows que:
- Pueden tomar minutos (análisis de inbox completo)
- Necesitan reintentos con backoff
- Deben persistir estado entre fallos
- Ejecutan en paralelo (múltiples usuarios)

## Options Considered

### Option 1: Redis + Celery
**Pros:**
- Celery es el estándar Python para tasks
- Redis como broker es rápido y simple
- Reintentos, scheduling, prioridades built-in
- Celery Beat para tasks periódicos (weekly digest)
- Bien documentado

**Cons:**
- Más componentes que manejar
- Redis necesita persistencia config

### Option 2: AWS SQS + Lambda
**Pros:**
- Serverless, escala automático
- Pay per use

**Cons:**
- Vendor lock-in
- Cold starts
- Más complejo para workflows largos

### Option 3: RQ (Redis Queue)
**Pros:**
- Más simple que Celery
- Menos overhead

**Cons:**
- Menos features
- Sin scheduling built-in
- Menos ecosystem

## Decision
**Redis + Celery** - Mejor balance de features y simplicidad. Celery Beat para weekly digests es critical.

## Consequences
- Redis como broker y result backend
- Celery workers en containers separados
- Celery Beat para scheduled tasks
- Flower para monitoring de queues
- LangGraph checkpoints guardados en PostgreSQL (no Redis)

## References
- [Celery docs](https://docs.celeryq.dev/)
- [Celery + Redis](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)
