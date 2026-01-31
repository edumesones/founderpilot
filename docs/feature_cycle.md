# Feature Development Cycle v2.0

## Objetivo

Este documento define el flujo de trabajo exacto para implementar cualquier feature, **incluyendo gestión de contexto integrada** para mantener trazabilidad total y permitir recuperación de sesiones interrumpidas.

---

## Resumen Visual

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     FEATURE DEVELOPMENT CYCLE v2.0                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   1. INTERVIEW      2. PLAN         3. BRANCH       4. IMPLEMENT                │
│   ┌─────────┐      ┌─────────┐     ┌─────────┐     ┌─────────┐                 │
│   │Preguntas│ ───► │ Explorar│ ──► │  git    │ ──► │ Código  │                 │
│   │Decisiones│     │ Diseñar │     │checkout │     │ Tests   │                 │
│   │ spec.md │      │ Plan.md │     │   -b    │     │ Commits │                 │
│   └────┬────┘      └────┬────┘     └────┬────┘     └────┬────┘                 │
│        │                │               │               │                       │
│        ▼                ▼               ▼               ▼                       │
│   📋 CONTEXT       📋 CONTEXT      📋 CONTEXT     📋 CONTEXT                   │
│   checkpoint       checkpoint      checkpoint     continuo                      │
│                                                        │                        │
│                                                        ▼                        │
│   7. WRAP-UP        6. MERGE        5. PR         ◄────┘                        │
│   ┌─────────┐      ┌─────────┐     ┌─────────┐                                  │
│   │ Archive │ ◄─── │ Review  │ ◄── │  Push   │                                  │
│   │ Learn   │      │ Approve │     │  gh pr  │                                  │
│   │ Clean   │      │ Update  │     │ create  │                                  │
│   └─────────┘      └─────────┘     └─────────┘                                  │
│       │                                                                          │
│       ▼                                                                          │
│   📦 Feature archived con contexto completo                                     │
│   📊 Aprendizajes documentados                                                  │
│   🧹 Contexto temporal limpiado                                                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Estructura de Contexto por Feature

```
docs/features/FEAT-XXX/
├── spec.md              # Especificación (Interview)
├── design.md            # Diseño técnico (Plan)
├── tasks.md             # Checklist de tareas (Implement)
├── tests.md             # Plan y resultados de tests
├── status.md            # Estado actual de la feature
└── context/             # 🆕 CONTEXTO DE SESIÓN
    ├── session_log.md   # Log cronológico de la sesión
    ├── decisions.md     # Decisiones tomadas durante desarrollo
    ├── blockers.md      # Blockers encontrados y resoluciones
    └── wrap_up.md       # Resumen final (post-merge)
```

---

## ⚠️ REGLA CRÍTICA: DOCUMENTACIÓN VIVA + CONTEXTO CONTINUO

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    📋 DOCUMENTATION & CONTEXT RULES                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   La documentación NO se actualiza "al final". Se actualiza EN TIEMPO REAL.     │
│   El contexto se captura EN CADA FASE, no solo al final.                        │
│                                                                                  │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ tasks.md - ACTUALIZAR EN CADA TASK                                    │     │
│   ├───────────────────────────────────────────────────────────────────────┤     │
│   │ ANTES de empezar task:    - [ ] Task 1  →  - [🟡] Task 1             │     │
│   │ DESPUÉS de completar:     - [🟡] Task 1  →  - [x] Task 1             │     │
│   │ Si hay problema:          - [🟡] Task 1  →  - [🔴] Task 1 (blocked)  │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ status.md - ACTUALIZAR EN CADA CAMBIO DE FASE                         │     │
│   ├───────────────────────────────────────────────────────────────────────┤     │
│   │ Interview completado  → Phase: Interview ✅                           │     │
│   │ Plan aprobado         → Phase: Plan ✅                                │     │
│   │ Branch creado         → Phase: Branch ✅, Current: Implement          │     │
│   │ Cada 3 tasks          → Progress: 3/10 tasks                          │     │
│   │ Blocker encontrado    → Blockers: [descripción]                       │     │
│   │ PR creado             → Phase: PR, Link: [url]                        │     │
│   │ Merged                → Status: 🟢 Complete                           │     │
│   │ Wrap-up done          → Status: 🟢 Complete + Wrapped ✅              │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ context/session_log.md - CHECKPOINT EN CADA FASE                      │     │
│   ├───────────────────────────────────────────────────────────────────────┤     │
│   │ Al completar Interview → Checkpoint con decisiones clave              │     │
│   │ Al completar Plan      → Checkpoint con arquitectura elegida          │     │
│   │ Al crear Branch        → Checkpoint con estado inicial                │     │
│   │ Durante Implement      → Log cada 30 min o 3 tasks                    │     │
│   │ Al crear PR            → Checkpoint con resumen de cambios            │     │
│   │ Al Merge               → Checkpoint de confirmación                   │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ _index.md (dashboard) - ACTUALIZAR EN CAMBIO DE STATUS                │     │
│   ├───────────────────────────────────────────────────────────────────────┤     │
│   │ Feature empieza       → ⚪ Pending  →  🟡 In Progress                 │     │
│   │ PR creado             → 🟡 In Progress  →  🔵 In Review               │     │
│   │ Merged                → 🔵 In Review  →  🟢 Complete                  │     │
│   │ Bloqueado             → 🟡 In Progress  →  🔴 Blocked                 │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   ⏰ COMMIT DOCS + CONTEXT CADA 30 MINUTOS O CADA 3 TASKS                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Marcadores de Tasks

| Marcador | Significado | Cuándo usar |
|----------|-------------|-------------|
| `- [ ]` | Pendiente | Task no iniciada |
| `- [🟡]` | En progreso | ANTES de empezar la task |
| `- [x]` | Completada | DESPUÉS de completar |
| `- [🔴]` | Bloqueada | Hay un impedimento |
| `- [⏭️]` | Saltada | Decidido no hacer (con nota) |

---

## Fase 1: INTERVIEW (Especificación)

### Propósito
Capturar TODAS las decisiones técnicas y de producto ANTES de escribir código.

### Comando
```
/interview FEAT-XXX
```
o
```
"Interview me about FEAT-XXX"
```

### Proceso

1. **Claude hace preguntas estructuradas** (máx 3-4 por turno):
   - UI/UX decisions
   - Comportamiento del sistema
   - Edge cases
   - Límites y restricciones
   - Integraciones

2. **El usuario responde con opciones claras**:
   - ✅ BIEN: "Import desde .env (DATABASE_URL format)"
   - ✅ BIEN: "Retry 3x automático + notificación"
   - ❌ MAL: "No sé, lo que tú creas"

3. **Claude actualiza spec.md** con cada decisión en formato tabla

### 📋 Context Checkpoint - Interview

```markdown
# En context/session_log.md añadir:

### [YYYY-MM-DD HH:MM] - Interview Complete ✅

**Fase:** Interview → Complete
**Duración:** ~X minutos

**Decisiones clave tomadas:**
- [Decisión 1]: [Valor elegido] - [Razón]
- [Decisión 2]: [Valor elegido] - [Razón]

**Preguntas pendientes:**
- [Si quedó algo por resolver]

**Próximo paso:** /plan FEAT-XXX
```

### 📄 Documentos actualizados
- `spec.md` → Decisiones documentadas
- `status.md` → Phase: Interview ✅
- `context/session_log.md` → Checkpoint de interview
- `context/decisions.md` → Si hubo decisiones arquitectónicas importantes

---

## Fase 2: PLAN (Diseño Técnico)

### Propósito
Diseñar la implementación ANTES de escribir código.

### Comando
```
/plan FEAT-XXX
```

### Proceso

1. Claude entra en **modo plan** (solo lectura, NO edita código)
2. Exploración del codebase existente
3. Genera plan con archivos, orden, snippets
4. Usuario revisa y aprueba

### 📋 Context Checkpoint - Plan

```markdown
# En context/session_log.md añadir:

### [YYYY-MM-DD HH:MM] - Plan Complete ✅

**Fase:** Plan → Complete

**Arquitectura elegida:**
- [Patrón/approach principal]

**Archivos a crear:** X nuevos
**Archivos a modificar:** Y existentes
**Tasks generadas:** Z tasks

**Dependencias identificadas:**
- [Externas: libs, APIs]
- [Internas: otros módulos]

**Riesgos técnicos:**
- [Riesgo 1]: [Mitigación]

**Próximo paso:** Crear branch
```

### 📄 Documentos actualizados
- `design.md` → Arquitectura técnica
- `tasks.md` → Checklist ordenado con todas las tasks
- `status.md` → Phase: Plan ✅
- `context/session_log.md` → Checkpoint de plan
- `context/decisions.md` → Decisiones de diseño

---

## Fase 3: BRANCH (Preparación)

### ⚠️ REGLA CRÍTICA
```
╔═══════════════════════════════════════════════════════════════╗
║  NUNCA EMPEZAR A CODEAR SIN CREAR LA RAMA PRIMERO            ║
╚═══════════════════════════════════════════════════════════════╝
```

### Proceso
```bash
git checkout main
git pull
git checkout -b feature/XXX-nombre-descriptivo
```

### Convención de Nombres
```
feature/001-auth           ✅ (número + descripción)
feature/002-db-connection  ✅
feat-001                   ❌ (muy corto)
nueva-feature              ❌ (no descriptivo)
```

### 📋 Context Checkpoint - Branch

```markdown
# En context/session_log.md añadir:

### [YYYY-MM-DD HH:MM] - Branch Created ✅

**Fase:** Branch → Complete
**Branch:** feature/XXX-nombre
**Base:** main @ [commit hash corto]

**Estado del repo:**
- Working tree clean: ✅
- Synced with origin: ✅

**Próximo paso:** Implement Task 1
```

### 📄 Documentos actualizados
- `status.md` → Phase: Branch ✅, Branch: feature/XXX-nombre
- `context/session_log.md` → Checkpoint de branch

---

## Fase 4: IMPLEMENT (Desarrollo)

### Propósito
Implementar siguiendo el plan, con documentación viva.

### ⚠️ FLUJO OBLIGATORIO POR CADA TASK

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         POR CADA TASK                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   1. ANTES DE EMPEZAR                                                           │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ □ Actualizar tasks.md:  - [ ] Task N  →  - [🟡] Task N               │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                              │                                                   │
│                              ▼                                                   │
│   2. IMPLEMENTAR                                                                │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ □ Escribir código                                                     │     │
│   │ □ Escribir tests (si aplica)                                          │     │
│   │ □ Verificar que funciona                                              │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                              │                                                   │
│                              ▼                                                   │
│   3. DESPUÉS DE COMPLETAR                                                       │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ □ Actualizar tasks.md:  - [🟡] Task N  →  - [x] Task N               │     │
│   │ □ git add [archivos de esta task]                                     │     │
│   │ □ git commit -m "FEAT-XXX: Complete Task N - descripción"            │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                              │                                                   │
│                              ▼                                                   │
│   4. CHECKPOINT (cada 30 min o 3 tasks)                                         │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ □ Actualizar status.md: Progress: X/Y tasks                           │     │
│   │ □ Actualizar context/session_log.md                                   │     │
│   │ □ git add docs/features/FEAT-XXX/                                     │     │
│   │ □ git commit -m "FEAT-XXX: Update progress X/Y"                       │     │
│   │ □ git push (backup remoto)                                            │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 📋 Context Logging - Durante Implement

```markdown
# En context/session_log.md añadir cada checkpoint:

### [YYYY-MM-DD HH:MM] - Implement Progress

**Progreso:** 5/12 tasks (42%)
**Última task completada:** B3 - Create UserService

**Cambios esta sesión:**
- Creado: src/services/user_service.py
- Creado: tests/test_user_service.py
- Modificado: src/main.py

**Decisiones tomadas:**
- Usar async para operaciones DB (performance)

**Problemas encontrados:**
- [Ninguno] o [Descripción + resolución]

**Próxima task:** B4 - Create API endpoints

**Tiempo en sesión:** ~1h 30min
```

### Si hay BLOCKER

```markdown
# En context/blockers.md añadir:

### 🔴 BLK-001: [Título del blocker]

**Detectado:** YYYY-MM-DD HH:MM
**Task afectada:** [Task ID]
**Severidad:** Alta/Media/Baja

**Descripción:**
[Qué está bloqueando]

**Intentos de resolución:**
1. [Intento 1] → [Resultado]

**Status:** 🔴 Activo / 🟢 Resuelto

**Resolución (cuando aplique):**
[Cómo se resolvió]
```

### Orden de Implementación Típico
1. Utilidades/helpers primero
2. Modelos de datos
3. Lógica de negocio / servicios
4. API endpoints / UI
5. Integración con sistema existente
6. Tests

### Reglas de Implementación

| ✅ HACER | ❌ NO HACER |
|----------|-------------|
| Un archivo/módulo a la vez | Implementar todo de golpe |
| Commit después de cada task | Commits gigantes |
| Tests para cada módulo nuevo | Saltarse los tests |
| Seguir patrones existentes | Inventar nuevos patrones |
| Actualizar docs en tiempo real | Dejar docs para el final |
| Context checkpoint cada 30 min | Olvidar el contexto |

### 📄 Documentos actualizados (CONTINUAMENTE)
- `tasks.md` → Marcadores actualizados por cada task
- `status.md` → Progress actualizado cada 3 tasks
- `context/session_log.md` → Log continuo de progreso
- `context/blockers.md` → Si hay blockers
- `context/decisions.md` → Si hay decisiones importantes

---

## Fase 5: PR (Pull Request)

### Comando
```
/git pr
```

### Proceso

```bash
# 1. Verificar estado
git status
git diff --stat --no-pager

# 2. Asegurar todo commiteado
git add .
git commit -m "FEAT-XXX: Final adjustments"

# 3. Push
git push -u origin feature/XXX-nombre

# 4. Crear PR
gh pr create --title "FEAT-XXX: Nombre Descriptivo" --body "$(cat <<'EOF'
## Summary
[1-3 bullets de qué hace]

## Features
- [x] Feature 1
- [x] Feature 2

## Files Changed
**New:** src/module/...
**Modified:** src/main.py

## Tests
- X unit tests ✅
- Y integration tests ✅

## Checklist
- [x] Tests passing
- [x] Docs updated
- [x] No console.logs / prints
EOF
)" --base main
```

### 📋 Context Checkpoint - PR

```markdown
# En context/session_log.md añadir:

### [YYYY-MM-DD HH:MM] - PR Created ✅

**Fase:** PR → Created
**PR:** #123 - [url completa]
**Branch:** feature/XXX-nombre → main

**Resumen de cambios:**
- Archivos nuevos: X
- Archivos modificados: Y
- Tests añadidos: Z
- Líneas: +A / -B

**Cobertura:** X%

**Reviewer:** [si asignado]
```

### 📄 Documentos actualizados
- `status.md` → Phase: PR ✅, PR: #123 [url]
- `_index.md` → Status: 🔵 In Review
- `context/session_log.md` → Checkpoint de PR

---

## Fase 6: MERGE (Cierre)

### Proceso

1. **Review** del PR
2. **Aprobar y Merge** en GitHub
3. **Actualizar documentación**:
   ```
   "Update FEAT-XXX status to complete"
   ```
4. **Limpiar rama local**:
   ```bash
   git checkout main
   git pull
   git branch -d feature/XXX-nombre
   ```

### 📋 Context Checkpoint - Merge

```markdown
# En context/session_log.md añadir:

### [YYYY-MM-DD HH:MM] - Merged ✅

**Fase:** Merge → Complete
**PR:** #123 merged
**Commit en main:** [hash]

**Próximo paso:** /wrap-up FEAT-XXX
```

### 📄 Documentos actualizados
- `status.md` → Status: 🟢 Complete, Merged: [date]
- `_index.md` → Status: 🟢 Complete
- `tests.md` → Results documentados
- `context/session_log.md` → Checkpoint de merge

---

## Fase 7: WRAP-UP (Context Closure) 🆕

### Propósito
Cerrar el ciclo de contexto, documentar aprendizajes y limpiar archivos temporales.

### Comando
```
/wrap-up FEAT-XXX
```

### ⚠️ ESTA FASE ES OBLIGATORIA
```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  NO HAY FEATURE COMPLETA SIN WRAP-UP                                          ║
║  El wrap-up captura conocimiento que se pierde si no se documenta ahora       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Proceso

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         WRAP-UP CHECKLIST                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   1. CREAR RESUMEN FINAL                                                        │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ □ Completar context/wrap_up.md con template                           │     │
│   │ □ Documentar tiempo total invertido                                   │     │
│   │ □ Listar todas las decisiones clave                                   │     │
│   │ □ Documentar deuda técnica creada (si aplica)                         │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   2. CAPTURAR APRENDIZAJES                                                      │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ □ ¿Qué funcionó bien?                                                 │     │
│   │ □ ¿Qué se podría mejorar?                                             │     │
│   │ □ ¿Hay patrones reutilizables?                                        │     │
│   │ □ ¿Algo que añadir a CLAUDE.md?                                       │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   3. LIMPIAR CONTEXTO TEMPORAL                                                  │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ □ Revisar .claude/context/mcp/FEAT-XXX_* → mover útiles o eliminar   │     │
│   │ □ Consolidar session_log.md (eliminar ruido si hay)                   │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   4. ACTUALIZAR DOCUMENTACIÓN GLOBAL (si aplica)                                │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ □ Si hay nuevo patrón → añadir a docs/patterns.md                     │     │
│   │ □ Si hay nueva regla → añadir a CLAUDE.md                             │     │
│   │ □ Actualizar README si cambió funcionalidad visible                   │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   5. COMMIT FINAL                                                               │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ □ git add docs/features/FEAT-XXX/context/                             │     │
│   │ □ git commit -m "FEAT-XXX: Add wrap-up documentation"                 │     │
│   │ □ git push                                                            │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 📄 Documentos actualizados
- `context/wrap_up.md` → Resumen final completo
- `context/session_log.md` → Entrada final de cierre
- `status.md` → Status: 🟢 Complete + Wrap-up ✅
- `CLAUDE.md` → Si hay nuevas reglas (opcional)

---

## Protocolo de Recuperación de Sesión (Resume)

### Cuándo usar
- Sesión interrumpida inesperadamente
- Retomando feature después de días/semanas
- Cambio de máquina o entorno

### Comando
```
/resume FEAT-XXX
```

### Proceso

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    RESUME PROTOCOL                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   1. LEER CONTEXTO EXISTENTE (en este orden)                                    │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ 1. docs/features/FEAT-XXX/status.md           # Estado actual         │     │
│   │ 2. docs/features/FEAT-XXX/context/session_log.md  # Último progreso  │     │
│   │ 3. docs/features/FEAT-XXX/tasks.md            # Tasks pendientes      │     │
│   │ 4. docs/features/FEAT-XXX/context/blockers.md # Blockers activos      │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   2. VERIFICAR ESTADO GIT                                                       │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ git branch --show-current                      # Verificar rama       │     │
│   │ git status                                     # Cambios pendientes   │     │
│   │ git log -n 3 --oneline                         # Últimos commits      │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   3. CREAR ENTRADA DE RESUME                                                    │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ Añadir a context/session_log.md:                                      │     │
│   │                                                                       │     │
│   │ ### [YYYY-MM-DD HH:MM] - Session Resumed 🔄                          │     │
│   │ **Última actividad:** [fecha del último log]                          │     │
│   │ **Días sin actividad:** X                                             │     │
│   │ **Estado encontrado:** [fase actual, progreso]                        │     │
│   │ **Continuando desde:** [task o acción]                                │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│   4. CONTINUAR DESDE DONDE QUEDÓ                                                │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Trabajo en Paralelo (Fork)

### Cuándo usar Fork
- Feature grande que se puede dividir (backend + frontend)
- Quieres acelerar desarrollo
- Tasks independientes que no se pisan

### Comando
```
/fork-feature FEAT-XXX backend
/fork-feature FEAT-XXX frontend
```

### Cómo funciona

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PARALLEL WORK WITH FORK                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Terminal Principal (tú)                                                       │
│   ┌───────────────────────────────────────────────────────────────────────┐     │
│   │ Orquesta, revisa, hace tareas que no se pueden paralelizar            │     │
│   └───────────────────────────────────────────────────────────────────────┘     │
│        │                                                                         │
│        ├──► /fork-feature FEAT-001 backend                                      │
│        │    ┌───────────────────────────────────────────────────────────┐       │
│        │    │ Nueva terminal con contexto de FEAT-001                   │       │
│        │    │ Solo trabaja en tasks de Backend                          │       │
│        │    │ Actualiza tasks.md Y context/session_log.md               │       │
│        │    └───────────────────────────────────────────────────────────┘       │
│        │                                                                         │
│        └──► /fork-feature FEAT-001 frontend                                     │
│             ┌───────────────────────────────────────────────────────────┐       │
│             │ Nueva terminal con contexto de FEAT-001                   │       │
│             │ Solo trabaja en tasks de Frontend                         │       │
│             │ Actualiza tasks.md Y context/session_log.md               │       │
│             └───────────────────────────────────────────────────────────┘       │
│                                                                                  │
│   ⚠️  IMPORTANTE:                                                               │
│   • Ambos trabajan en MISMA RAMA                                                │
│   • git pull frecuente para evitar conflictos                                   │
│   • Cada fork actualiza SU SECCIÓN de tasks.md                                  │
│   • Prefijo en session_log.md: [FORK:backend] o [FORK:frontend]                │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Context en Forks
Cada fork añade prefijo a sus entradas:
```markdown
### [YYYY-MM-DD HH:MM] - [FORK:backend] Task B3 complete
```

---

## Checklist Rápido

```
□ INTERVIEW
  □ Preguntas hechas
  □ Decisiones en spec.md
  □ status.md → Phase: Interview ✅
  □ context/session_log.md → Checkpoint ✅

□ PLAN  
  □ Codebase explorado
  □ design.md creado
  □ tasks.md con checklist
  □ status.md → Phase: Plan ✅
  □ context/session_log.md → Checkpoint ✅

□ BRANCH
  □ git checkout -b feature/XXX
  □ status.md → Branch creado
  □ context/session_log.md → Checkpoint ✅

□ IMPLEMENT
  □ Por cada task:
    □ Marcar 🟡 antes
    □ Implementar
    □ Marcar ✅ después
    □ Commit
  □ Checkpoint cada 30 min o 3 tasks:
    □ context/session_log.md actualizado
    □ git push

□ PR
  □ Todo commiteado
  □ gh pr create
  □ status.md → PR link
  □ context/session_log.md → Checkpoint ✅

□ MERGE
  □ Review aprobado
  □ Merged
  □ status.md → 🟢 Complete
  □ _index.md actualizado
  □ Rama local borrada
  □ context/session_log.md → Checkpoint ✅

□ WRAP-UP (OBLIGATORIO)
  □ context/wrap_up.md completado
  □ Métricas documentadas
  □ Aprendizajes capturados
  □ Deuda técnica identificada
  □ Temporales limpiados
  □ CLAUDE.md actualizado si aplica
  □ status.md → Wrap-up ✅
  □ Commit y push final
```

---

## Anti-Patterns

| ❌ Anti-Pattern | ✅ Correcto |
|----------------|-------------|
| Codear sin interview | Interview primero |
| Codear sin rama | Rama antes de código |
| Codear sin plan | Plan primero |
| Actualizar docs al final | Docs en tiempo real |
| Commits gigantes | Commit por task |
| Ignorar tests | Tests obligatorios |
| Fork sin contexto | Fork con /fork-feature |
| Terminar sin wrap-up | Wrap-up obligatorio |
| No loguear decisiones | Log continuo en context/ |
| Perder contexto entre sesiones | Usar /resume |

---

## Comandos Disponibles - Quick Reference

| Comando | Fase | Propósito |
|---------|------|-----------|
| `/new-project` | Setup | Crear estructura de proyecto |
| `/project-interview` | Setup | Definir proyecto |
| `/architecture` | Setup | Definir arquitectura y ADRs |
| `/mvp` | Setup | Planificar MVP features |
| `/new-feature FEAT-XXX` | Pre-cycle | Crear feature desde template |
| `/interview FEAT-XXX` | 1. Interview | Especificar feature |
| `/plan FEAT-XXX` | 2. Plan | Diseñar implementación |
| `/git sync` | 3+ | Sincronizar con main |
| `/git "mensaje"` | 4. Implement | Commit con mensaje |
| `/git pr` | 5. PR | Crear pull request |
| `/fork-feature FEAT-XXX role` | 4. Implement | Trabajo paralelo |
| `/resume FEAT-XXX` | Any | Retomar feature |
| `/wrap-up FEAT-XXX` | 7. Wrap-up | Cerrar feature |
| `/log "mensaje"` | Any | Añadir entrada manual |

---

*Última actualización: {date}*
*Versión: 2.0 - Con Context Management integrado*
