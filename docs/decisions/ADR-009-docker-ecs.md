# ADR-009: Docker + AWS ECS para Deployment

## Status
Accepted

## Date
2026-01-31

## Context
FounderPilot necesita:
- Desarrollo local idéntico a producción
- Múltiples servicios (API, workers, Redis, PostgreSQL)
- Escalado horizontal de workers
- Deployment simple para solo founder
- Costos controlados para MVP

## Options Considered

### Option 1: Docker Compose (dev) + AWS ECS (prod)
**Pros:**
- Docker Compose: desarrollo local simple
- ECS: managed containers sin Kubernetes complexity
- Fargate: serverless containers, pay-per-use
- Escala workers independientemente
- AWS ecosystem (RDS, ElastiCache, etc.)

**Cons:**
- Vendor lock-in (AWS)
- ECS learning curve

### Option 2: Kubernetes (EKS)
**Pros:**
- Estándar de la industria
- Muy flexible

**Cons:**
- Overkill para MVP
- Complejidad alta
- Costo mínimo ~$70/mes solo por control plane

### Option 3: Railway/Render
**Pros:**
- Deploy desde Git
- Muy simple

**Cons:**
- Menos control
- Más caro a escala
- Menos ecosystem

## Decision
**Docker Compose para desarrollo + AWS ECS Fargate para producción**

Estructura de servicios:
```
├── api          (FastAPI)
├── worker       (Celery workers)
├── beat         (Celery beat scheduler)
├── redis        (ElastiCache en prod)
├── postgres     (RDS en prod)
└── frontend     (Vercel - separado)
```

## Consequences
- Dockerfile por cada servicio
- docker-compose.yml para desarrollo local
- ECS Task Definitions para producción
- GitHub Actions para CI/CD
- Frontend en Vercel (más simple para Next.js)

## References
- [ECS Fargate](https://aws.amazon.com/fargate/)
- [Docker Compose](https://docs.docker.com/compose/)
