# ADR-001: Python + LangGraph para Agent Framework

## Status
Accepted

## Date
2026-01-31

## Context
FounderPilot necesita un framework para construir agentes autónomos que:
- Soporten human-on-the-loop (aprobación humana para acciones críticas)
- Manejen workflows con estado durable
- Permitan control granular sobre el flujo de ejecución
- Sean debuggeables y observables

## Options Considered

### Option 1: LangGraph
**Pros:**
- Graph-based: flujo visual y debuggeable
- Human-in-the-loop nativo con interrupts
- Estado persistente entre ejecuciones
- Control granular sobre cada nodo
- Integración directa con LangChain ecosystem

**Cons:**
- Curva de aprendizaje para grafos
- Más verbose que alternativas

### Option 2: CrewAI
**Pros:**
- Más simple para multi-agent
- Role-based (asignas "roles" a agentes)
- Backed by AI Fund (Andrew Ng)

**Cons:**
- Menos control granular
- Human-in-loop menos maduro
- Más opinionated

### Option 3: AutoGen (Microsoft)
**Pros:**
- Conversational agents naturales
- Buen soporte enterprise

**Cons:**
- Más orientado a chat que workflows
- Menos control sobre estado

## Decision
**LangGraph** - El control granular y human-in-loop nativo son críticos para nuestro diferenciador de "transparencia y control".

## Consequences
- Usaremos grafos para definir workflows de agentes
- Cada nodo será una "step" auditable
- Implementaremos checkpoints para estado durable
- Los interrupts permitirán escalation a humanos

## References
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [Human-in-the-loop patterns](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
