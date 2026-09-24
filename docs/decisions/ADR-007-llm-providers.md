# ADR-007: Multi-Provider LLM Strategy

## Status
Accepted

## Date
2026-01-31

## Context
FounderPilot hace múltiples tipos de llamadas a LLMs:
- Classification (rápido, barato): categorizar emails
- Generation (calidad): draft responses, summaries
- Analysis (complejo): meeting prep, weekly digest

Necesitamos:
- Reliability (fallback si un provider falla)
- Cost optimization (usar modelo adecuado para cada task)
- Flexibility (cambiar providers sin rewrite)

## Options Considered

### Option 1: Multi-provider (Claude + GPT-4o)
**Pros:**
- Fallback automático
- Best model for each task
- No vendor lock-in
- Cost optimization por tier

**Cons:**
- Más complejidad
- Dos APIs que mantener
- Prompts pueden variar

### Option 2: Solo OpenAI
**Pros:**
- Un solo provider
- Ecosystem maduro
- GPT-4o es muy capaz

**Cons:**
- Single point of failure
- Sin fallback
- Vendor lock-in

### Option 3: Solo Anthropic
**Pros:**
- Claude es excelente para analysis
- Mejor reasoning

**Cons:**
- API menos madura que OpenAI
- Sin fallback

## Decision
**Multi-provider con routing inteligente:**

| Task Type | Primary | Fallback | Rationale |
|-----------|---------|----------|-----------|
| Classification | GPT-4o-mini | Claude Haiku | Rápido, barato |
| Generation | Claude Sonnet | GPT-4o | Mejor calidad texto |
| Analysis | Claude Opus | GPT-4o | Reasoning complejo |

## Consequences
- Abstracción de LLM provider (LiteLLM o custom)
- Retry con fallback automático
- Tracking de costs por provider y task type
- Prompts versionados por modelo cuando necesario

## References
- [LiteLLM](https://docs.litellm.ai/)
- [Anthropic API](https://docs.anthropic.com/)
- [OpenAI API](https://platform.openai.com/docs/)
