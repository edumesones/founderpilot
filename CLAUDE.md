# FounderPilot

Asistente multi-tenant para fundadores: tres agentes que trabajan sobre correo, facturas y reuniones,
con revisión humana antes de cualquier acción con efecto.

## Arquitectura

| Capa | Qué hay |
|---|---|
| API | FastAPI + SQLAlchemy async sobre Postgres, migraciones con Alembic |
| Tareas | Celery + Redis |
| Agentes | LangGraph. `InboxPilot` (triaje de Gmail), `InvoicePilot`, `MeetingPilot` |
| Frontend | Next.js + React |
| Facturación | Stripe con medición de uso |

## Las dos decisiones que mandan

**Human in the loop, no confianza en el modelo.** Los agentes paran con `interrupt_before` y el estado
queda en Postgres. Nada con efecto externo se ejecuta sin que una persona lo apruebe por Slack. Si el
proceso se cae, el checkpoint permite reanudar sin repetir acciones.

**Auditoría como funcionalidad de producto, no como log.** Cada acción de agente queda registrada con su
puntuación de confianza y su escalado. El panel de auditoría es una pantalla del producto, no un fichero
de texto para el que lo depure.

## Comandos

```bash
docker compose up -d          # Postgres y Redis
alembic upgrade head          # migraciones
uvicorn src.main:app --reload # API
pytest                        # tests
cd frontend && npm run dev    # frontend
```

## Reglas del repo

- Ninguna acción con efecto externo sin punto de control humano.
- Todo agente escribe en el registro de auditoría: sin excepción.
- Las migraciones son lineales. Si dos añaden el mismo número, la cadena está rota y hay que arreglarla
  antes de seguir.
