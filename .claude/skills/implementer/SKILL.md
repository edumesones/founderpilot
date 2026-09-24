---
name: implementer
description: Execute feature tasks one by one with live documentation and context logging. Triggers on "Execute FEAT-XXX tasks", "Start implementing FEAT-XXX", "Work on FEAT-XXX", "Continue FEAT-XXX".
globs: ["docs/features/**/tasks.md", "docs/features/**/status.md", "docs/features/**/context/*", "src/**", "tests/**"]
---

# Implementer

Execute feature tasks one by one with live documentation and context updates.

## Triggers

- "Execute FEAT-XXX tasks"
- "Start implementing FEAT-XXX"
- "Work on FEAT-XXX"
- "Continue FEAT-XXX"
- "Resume FEAT-XXX"
- "Next task for FEAT-XXX"

## Prerequisites

- Feature folder exists with completed:
  - `spec.md` ✅
  - `design.md` ✅
  - `tasks.md` ✅
  - `context/` folder with templates ✅
- Git branch created for feature
- If missing: guide user to complete previous phases

## Purpose

1. **Find next uncompleted task** in tasks.md
2. **Execute task** (write code, create files, etc.)
3. **Update documentation** in real-time
4. **Update context** (session_log, decisions, blockers)
5. **Commit** after each task
6. **Repeat** until all tasks done or blocker hit

## Process

### 1. Read Context

```bash
# Read tasks
cat docs/features/FEAT-XXX/tasks.md

# Read design for reference
cat docs/features/FEAT-XXX/design.md

# Read spec for requirements
cat docs/features/FEAT-XXX/spec.md

# Check current status
cat docs/features/FEAT-XXX/status.md

# Read last session log entries
tail -30 docs/features/FEAT-XXX/context/session_log.md

# Check for active blockers
cat docs/features/FEAT-XXX/context/blockers.md

# Verify git branch
git branch --show-current
```

### 2. Verify Branch

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  BRANCH CHECK                                                                  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  If on main/master:                                                           ║
║  → STOP and say: "Create feature branch first:                                ║
║    git checkout -b feature/XXX-name"                                          ║
║                                                                                ║
║  If on correct feature branch:                                                ║
║  → Continue with implementation                                               ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 3. Find Next Task

Scan tasks.md for first task that is:
- `[ ]` Pending, OR
- `[🟡]` In Progress (resume)

Skip tasks that are:
- `[x]` Complete
- `[⏭️]` Skipped
- `[🔴]` Blocked

### 4. Execute Task Loop

For each task:

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  TASK EXECUTION FLOW                                                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  A. BEFORE starting:                                                           ║
║     1. Update tasks.md: [ ] → [🟡]                                            ║
║     2. Announce: "Starting task: [task description]"                          ║
║                                                                                ║
║  B. DURING execution:                                                          ║
║     1. Write code / create files                                              ║
║     2. Follow design.md specifications                                        ║
║     3. If unclear → ask user, don't assume                                    ║
║     4. If blocked → mark [🔴], log to blockers.md, move to next               ║
║     5. If decision needed → log to decisions.md                               ║
║                                                                                ║
║  C. AFTER completing:                                                          ║
║     1. Update tasks.md: [🟡] → [x]                                            ║
║     2. Update progress table in tasks.md                                      ║
║     3. Commit: git add . && git commit -m "FEAT-XXX: [task]"                  ║
║     4. Announce: "✅ Task complete. Progress: X/Y tasks"                      ║
║                                                                                ║
║  D. CHECKPOINT (every 30 min or 3 tasks):                                      ║
║     1. Update status.md with progress                                         ║
║     2. Update context/session_log.md                                          ║
║     3. git push origin [branch]                                               ║
║     4. Summary of progress                                                    ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 5. Context Logging (CRITICAL)

**After EVERY 3 tasks, add to context/session_log.md:**

```markdown
### [YYYY-MM-DD HH:MM] - Implement Progress

**Progreso:** X/Y tasks (XX%)
**Tasks completadas esta sesión:**
- [x] Task N - descripción
- [x] Task N+1 - descripción
- [x] Task N+2 - descripción

**Archivos modificados:**
- src/module/file.py (nuevo)
- tests/test_module.py (nuevo)

**Decisiones tomadas:**
- [Decisión si hubo alguna]

**Problemas encontrados:**
- [Ninguno] o [descripción + resolución]

**Próxima task:** Task N+3 - descripción

**Tiempo en sesión:** ~X minutos
```

**If BLOCKER found, add to context/blockers.md:**

```markdown
### 🔴 BLK-XXX: [Título]

**Detectado:** YYYY-MM-DD HH:MM
**Task afectada:** [Task ID]
**Severidad:** Alta/Media/Baja
**Status:** 🔴 Activo

**Descripción:**
[Qué bloquea]

**Intentos:**
1. [Intento] → [Resultado]

**Próximos pasos:**
- [Qué intentar]
```

**If DECISION made, add to context/decisions.md:**

```markdown
### DEC-XXX: [Título]

**Fecha:** YYYY-MM-DD
**Fase:** Implement
**Task:** [Task relacionada]

**Contexto:** [Por qué surgió]

**Opciones:**
1. [Opción A] - Pros/Cons
2. [Opción B] - Pros/Cons

**Decisión:** [Elegida]
**Razón:** [Por qué]
```

### 6. Task Documentation

**tasks.md updates:**

```markdown
# Before
- [ ] Create User model in src/models/user.py

# During  
- [🟡] Create User model in src/models/user.py

# After
- [x] Create User model in src/models/user.py
```

**Progress table update:**

```markdown
| Section | Progress | Tasks |
|---------|----------|-------|
| Backend | 🟡 25% | 2/8 |  ← UPDATE after each task
```

### 7. Commit Format

```bash
git add [specific files for this task]
git commit -m "FEAT-XXX: [Task description]"
```

**Examples:**
```
FEAT-001: Create User model
FEAT-001: Add user validation schemas
FEAT-001: Implement UserService CRUD methods
FEAT-001: Add POST /users endpoint
FEAT-001: Add unit tests for UserService
```

### 8. Status Updates

**After EACH checkpoint (3 tasks), update:**

**status.md:**
```markdown
## Progress
- Tasks completed: X/Y
- Current task: [next task or "All complete"]
- Last update: {timestamp}
```

**_index.md (global):**
```markdown
| FEAT-XXX | [Name] | 🟡 In Progress | Implement (X/Y) |
```

### 9. Blocker Handling

If task cannot be completed:

1. **Mark in tasks.md:**
```markdown
- [🔴] Create payment integration (blocked: waiting for Stripe API keys)
```

2. **Log in context/blockers.md:**
```markdown
### 🔴 BLK-001: Missing Stripe API keys

**Detectado:** 2026-01-22 10:30
**Task afectada:** B5 - Payment integration
**Severidad:** Alta
**Status:** 🔴 Activo

**Descripción:**
Cannot test payment flow without API keys.

**Intentos:**
1. Check .env.example → No keys there
2. Ask user → Waiting for response

**Acción requerida:** User to provide Stripe test keys
```

3. **Update status.md blockers section**

4. **Continue with next unblocked task**

### 10. Completion

When all tasks done:

```
✅ FEAT-XXX implementation complete!

Summary:
- Total tasks: X
- Completed: X
- Skipped: X
- Blocked: X

Updated:
- docs/features/FEAT-XXX/tasks.md (all marked)
- docs/features/FEAT-XXX/status.md (Phase: Implement ✅)
- docs/features/FEAT-XXX/context/session_log.md (final entry)
- docs/features/_index.md (status updated)

Next steps:
1. Push: git push -u origin feature/XXX-name
2. Create PR: /git pr
3. After merge: /wrap-up FEAT-XXX
```

### 11. Final Session Log Entry

```markdown
### [YYYY-MM-DD HH:MM] - Implementation Complete ✅

**Fase:** Implement → Complete
**Progreso final:** X/Y tasks (100%)

**Resumen de sesión:**
- Tasks completadas: X
- Decisiones tomadas: Y (ver decisions.md)
- Blockers resueltos: Z

**Archivos creados:** [lista]
**Archivos modificados:** [lista]
**Tests añadidos:** X

**Próximo paso:** Create PR (/git pr)
```

## Pause/Resume

If user needs to stop:
- Current task stays as `[🟡]`
- Add pause entry to session_log.md:
```markdown
### [YYYY-MM-DD HH:MM] - Session Paused ⏸️

**Progreso:** X/Y tasks
**En progreso:** [Task actual]
**Tiempo en sesión:** ~X minutos

**Para retomar:** /resume FEAT-XXX
```

Resume with `/resume FEAT-XXX`

## Error Recovery

If something goes wrong:
- Don't mark task complete
- Ask user for guidance
- Document issue in context/blockers.md
- Log attempt in session_log.md
