# ADR-008: Langfuse + CloudWatch para Observability

## Status
Accepted

## Date
2026-01-31

## Context
FounderPilot necesita observabilidad en múltiples niveles:
- **LLM calls**: traces, latency, costs, token usage
- **Agent workflows**: qué decidió, por qué, resultado
- **Infrastructure**: CPU, memory, errors, uptime
- **Business metrics**: workflows completados, escalations, user satisfaction

## Options Considered

### Option 1: Langfuse + CloudWatch
**Pros:**
- Langfuse: específico para LLMs, traces detallados
- Integración nativa con LangGraph
- Dashboard de costs por usuario/workflow
- CloudWatch: infra monitoring gratis con ECS
- Separación de concerns clara

**Cons:**
- Dos sistemas
- Langfuse es otro servicio (aunque tiene self-host)

### Option 2: OpenTelemetry + Grafana
**Pros:**
- Estándar abierto
- Todo en uno

**Cons:**
- Setup complejo
- Sin LLM-specific features
- Más infra que mantener

### Option 3: Solo logging (CloudWatch Logs)
**Pros:**
- Simple
- Ya incluido en AWS

**Cons:**
- Sin traces de LLM
- Sin cost tracking
- Debugging difícil

## Decision
**Langfuse para LLM/Agent observability + CloudWatch para infra**

Langfuse nos da:
- Traces de cada LLM call con inputs/outputs
- Cost tracking por usuario y workflow
- Latency p50/p95/p99
- Dataset collection para mejora de prompts

## Consequences
- Langfuse SDK integrado en LangGraph callbacks
- Cada workflow tiene un trace_id único
- Audit logs vinculados a traces
- Alertas en CloudWatch para errores de infra
- Dashboard de Langfuse para LLM performance

## References
- [Langfuse docs](https://langfuse.com/docs)
- [Langfuse + LangGraph](https://langfuse.com/docs/integrations/langchain)
- [CloudWatch](https://aws.amazon.com/cloudwatch/)
