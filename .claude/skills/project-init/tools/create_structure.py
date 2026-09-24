#!/usr/bin/env python3
"""
Project Structure Creator for Claude Code Workflow.
Creates complete documentation and workflow structure for new projects.

Usage:
    python create_structure.py "ProjectName" "One-liner description"
    python create_structure.py  # Interactive mode
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# =============================================================================
# TEMPLATES
# =============================================================================

CLAUDE_MD = '''## 1. Qué es este proyecto
{project_name} - {description}
Stack: {stack}

## 2. Cómo trabajo
Sigo el ciclo en `docs/feature_cycle.md`:
Interview → Plan → Branch → Implement → PR → Merge

## 3. Estado actual
Ver `docs/features/_index.md` para dashboard completo.

## 4. Tu primer paso
1. Lee `docs/project.md` para entender el proyecto
2. Lee `docs/features/_index.md` para ver features pendientes
3. Si hay feature ⚪ Pending con spec.md template → "Interview me about FEAT-XXX"
4. Si hay feature con spec.md completo → "/plan implement FEAT-XXX"

## 5. Reglas importantes
- NUNCA codear sin rama creada
- NUNCA implementar sin plan aprobado
- Commits incrementales por tarea
- Tests obligatorios

## 6. Reglas de Terminal
- NO uses `watch` ni comandos que refrescan infinitamente
- Usa `--no-pager` con git: `git diff --no-pager`
- Usa `-n` para limitar output: `git log -n 5`
- Evita `tail -f` o cualquier stream infinito
- Si un comando produce mucho output, redirige a archivo
'''

README_MD = '''# {project_name}

{description}

## Quick Start

```bash
# Setup
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\\Scripts\\activate  # Windows
pip install -r requirements.txt

# Run
python src/main.py
```

## Documentation

- [Project Definition](docs/project.md)
- [Feature Dashboard](docs/features/_index.md)
- [Development Cycle](docs/feature_cycle.md)
- [Architecture](docs/architecture/_index.md)

## Development

This project follows a structured feature development cycle.
See `docs/feature_cycle.md` for the complete workflow.

```
Interview → Plan → Branch → Implement → PR → Merge
```

## Stack

{stack}

---
Created: {date}
'''

PROJECT_MD = '''# Project Definition

## Nombre
{project_name}

## One-liner
{description}

## Stack
- **Backend**: Python, FastAPI
- **Frontend**: Gradio / React
- **Database**: PostgreSQL / SQLite
- **Infrastructure**: Docker, GitHub Actions

## MVP Scope

### Incluido
- [ ] Feature 1
- [ ] Feature 2
- [ ] Feature 3

### Excluido (Post-MVP)
- Feature X
- Feature Y

## Target Users
[Describe para quién es este proyecto]

## Success Metrics
- Metric 1
- Metric 2

---
*Last updated: {date}*
'''

FEATURES_INDEX_MD = '''# Features Dashboard

## Overview

| ID | Nombre | Status | Sprint | Priority |
|----|--------|--------|--------|----------|
| FEAT-001 | [Nombre] | ⚪ Pending | MVP | P0 |

## Status Legend

| Icon | Status | Meaning |
|------|--------|---------|
| ⚪ | Pending | No iniciado |
| 🟡 | In Progress | En desarrollo |
| 🔵 | In Review | PR abierto |
| 🟢 | Complete | Mergeado |
| 🔴 | Blocked | Bloqueado |

## Priority Legend

| Priority | Meaning |
|----------|---------|
| P0 | Critical - MVP blocker |
| P1 | High - MVP nice to have |
| P2 | Medium - Post-MVP |
| P3 | Low - Future |

## Quick Links

- [Feature Template](_template/)
- [Development Cycle](../feature_cycle.md)
- [Architecture](../architecture/_index.md)

---
*Last updated: {date}*
'''

FEATURE_SPEC_MD = '''# FEAT-XXX: [Feature Name]

## Summary
[One paragraph describing what this feature does]

## User Stories
- Como [usuario] quiero [acción] para [beneficio]
- Como [usuario] quiero [acción] para [beneficio]

## Acceptance Criteria
- [ ] Criterio 1
- [ ] Criterio 2
- [ ] Criterio 3

## Technical Decisions

| Decisión | Valor | Notas |
|----------|-------|-------|
| [Decisión 1] | [Valor] | [Por qué] |
| [Decisión 2] | [Valor] | [Por qué] |

## Out of Scope
- Item 1
- Item 2

## Dependencies
- Depends on: [FEAT-XXX, ARCH-XXX]
- Blocks: [FEAT-YYY]

## Open Questions
- [ ] Question 1?
- [ ] Question 2?

---
*Status: ⚪ Pending*
*Created: {date}*
'''

FEATURE_DESIGN_MD = '''# FEAT-XXX: Technical Design

## Overview
[Brief technical overview of the implementation approach]

## Components

### New Files
```
src/
├── module/
│   ├── __init__.py
│   ├── models.py
│   └── service.py
tests/
└── test_module.py
```

### Modified Files
- `src/main.py` - Add router
- `requirements.txt` - Add dependencies

## Data Model

```python
# Example model
class Entity:
    id: int
    name: str
    created_at: datetime
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/resource | List resources |
| POST | /api/resource | Create resource |

## Sequence Diagram

```
User -> Frontend -> API -> Service -> Database
```

## Dependencies
- New packages: [list]
- External services: [list]

## Security Considerations
- [ ] Input validation
- [ ] Authentication required
- [ ] Rate limiting

## Performance Considerations
- Expected load: X requests/sec
- Caching strategy: [describe]

---
*Last updated: {date}*
'''

FEATURE_TASKS_MD = '''# FEAT-XXX: Tasks

## Pre-Implementation
- [ ] spec.md complete and approved
- [ ] design.md complete and approved
- [ ] Branch created: `feature/XXX-name`

## Backend Tasks
- [ ] Task 1: Create models
- [ ] Task 2: Create service layer
- [ ] Task 3: Create API endpoints
- [ ] Task 4: Add validation

## Frontend Tasks
- [ ] Task 5: Create UI components
- [ ] Task 6: Connect to API
- [ ] Task 7: Add error handling

## Testing Tasks
- [ ] Task 8: Unit tests for service
- [ ] Task 9: Unit tests for API
- [ ] Task 10: Integration tests

## Documentation Tasks
- [ ] Task 11: Update README
- [ ] Task 12: Add docstrings
- [ ] Task 13: Update API docs

## DevOps Tasks
- [ ] Task 14: Environment variables
- [ ] Task 15: CI/CD updates

## Post-Implementation
- [ ] PR created
- [ ] Code review complete
- [ ] Merged to main
- [ ] status.md updated

---
*Progress: 0/{total} tasks*
*Last updated: {date}*
'''

FEATURE_TESTS_MD = '''# FEAT-XXX: Test Cases

## Unit Tests

### Service Layer
| Test Case | Input | Expected Output | Status |
|-----------|-------|-----------------|--------|
| test_create_valid | valid data | success | ⚪ |
| test_create_invalid | invalid data | validation error | ⚪ |

### API Endpoints
| Test Case | Method | Endpoint | Expected Status | Status |
|-----------|--------|----------|-----------------|--------|
| test_list | GET | /api/resource | 200 | ⚪ |
| test_create | POST | /api/resource | 201 | ⚪ |

## Integration Tests

| Test Case | Description | Status |
|-----------|-------------|--------|
| test_e2e_flow | Complete user flow | ⚪ |

## Edge Cases

| Scenario | Expected Behavior | Status |
|----------|-------------------|--------|
| Empty input | Return validation error | ⚪ |
| Large payload | Handle gracefully | ⚪ |

## Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific feature tests
pytest tests/test_feat_xxx.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---
*Coverage Target: 80%*
*Last updated: {date}*
'''

FEATURE_STATUS_MD = '''# FEAT-XXX: Status

## Current Status: ⚪ Pending

## Progress

| Phase | Status | Date |
|-------|--------|------|
| Interview | ⚪ Pending | - |
| Plan | ⚪ Pending | - |
| Branch | ⚪ Pending | - |
| Implement | ⚪ Pending | - |
| PR | ⚪ Pending | - |
| Merge | ⚪ Pending | - |

## Task Progress

- Backend: 0/4 tasks
- Frontend: 0/3 tasks
- Tests: 0/3 tasks
- Docs: 0/3 tasks

## Blockers
- None

## Notes

### {date}
- Feature created

---
*Last updated: {date}*
'''

ARCHITECTURE_INDEX_MD = '''# Architecture Documentation

## Overview

[High-level architecture description]

## System Components

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Architecture Decision Records (ADRs)

| ID | Decision | Status | Date |
|----|----------|--------|------|
| ARCH-001 | [System Overview] | ✅ Accepted | {date} |

## Key Principles

1. **Principle 1**: Description
2. **Principle 2**: Description
3. **Principle 3**: Description

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Backend | FastAPI | Performance, async support |
| Frontend | Gradio | Rapid prototyping |
| Database | PostgreSQL | Reliability |

---
*Last updated: {date}*
'''

SPRINTS_INDEX_MD = '''# Sprints Dashboard

## Current Sprint

**SPRINT-001: MVP**
- Start: {date}
- End: TBD
- Goal: [Sprint goal]

## Sprint History

| Sprint | Goal | Status | Features |
|--------|------|--------|----------|
| SPRINT-001 | MVP | 🟡 Active | FEAT-001, FEAT-002 |

## Sprint Template

Each sprint folder contains:
- `goals.md` - Sprint objectives
- `features.md` - Features included
- `retro.md` - Retrospective notes

---
*Last updated: {date}*
'''

DECISIONS_INDEX_MD = '''# Architecture Decision Records (ADRs)

## What is an ADR?

An Architecture Decision Record captures an important architectural decision along with its context and consequences.

## ADR Template

```markdown
# ADR-XXX: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[What is the issue that we're seeing that is motivating this decision?]

## Decision
[What is the change that we're proposing and/or doing?]

## Consequences
[What becomes easier or more difficult to do because of this change?]
```

## ADR Index

| ID | Decision | Status | Date |
|----|----------|--------|------|
| ADR-001 | [First decision] | Proposed | {date} |

---
*Last updated: {date}*
'''

FEATURE_CYCLE_MD = '''# Feature Development Cycle

## Objetivo

Este documento define el flujo de trabajo exacto para implementar cualquier feature en este proyecto. Siguiendo este ciclo se garantiza consistencia, trazabilidad y calidad.

---

## Resumen Visual

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FEATURE DEVELOPMENT CYCLE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   1. INTERVIEW          2. PLAN            3. BRANCH         4. IMPLEMENT   │
│   ┌─────────┐          ┌─────────┐        ┌─────────┐       ┌─────────┐    │
│   │ Preguntas│   ───►  │ Explorar │  ───► │ git     │ ───►  │ Código  │    │
│   │ Decisiones│        │ Diseñar │        │ checkout│       │ Tests   │    │
│   │ spec.md  │         │ Plan.md │        │ -b      │       │ Commits │    │
│   └─────────┘          └─────────┘        └─────────┘       └─────────┘    │
│                                                                    │        │
│                                                                    ▼        │
│   6. MERGE              5. PR              ◄────────────────────────        │
│   ┌─────────┐          ┌─────────┐                                          │
│   │ Review  │   ◄───   │ Push    │                                          │
│   │ Approve │          │ gh pr   │                                          │
│   │ Update  │          │ create  │                                          │
│   └─────────┘          └─────────┘                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Fase 1: INTERVIEW (Especificación)

### Propósito
Capturar TODAS las decisiones técnicas y de producto ANTES de escribir código.

### Cómo Iniciar
```
"Interview me about FEAT-XXX"
```

### Proceso

1. **Claude hace preguntas estructuradas** sobre:
   - UI/UX decisions
   - Comportamiento del sistema
   - Edge cases
   - Límites y restricciones
   - Integraciones

2. **El usuario responde con opciones claras**:
   - ✅ BIEN: "Import desde .env (DATABASE_URL format)"
   - ✅ BIEN: "Retry 3x automático + notificación"
   - ❌ MAL: "No sé, lo que tú creas"

3. **Claude actualiza el spec.md** con cada decisión en formato tabla.

### Output
- `docs/features/FEAT-XXX/spec.md` actualizado con todas las decisiones

---

## Fase 2: PLAN (Diseño Técnico)

### Propósito
Diseñar la implementación ANTES de escribir código.

### Cómo Iniciar
```
/plan implement FEAT-XXX
```

### Proceso

1. Claude entra en modo plan (solo lectura, no edita código)
2. Exploración del codebase
3. Genera plan detallado con archivos, orden, snippets
4. Usuario revisa y aprueba

### Output
- `docs/features/FEAT-XXX/design.md` completado
- `docs/features/FEAT-XXX/tasks.md` con checklist

---

## Fase 3: BRANCH (Preparación)

### ⚠️ CRÍTICO
```
NUNCA empezar a codear sin crear la rama primero.
```

### Proceso
```bash
git checkout main
git checkout -b feature/XXX-nombre-descriptivo
```

---

## Fase 4: IMPLEMENT (Desarrollo)

### Proceso

1. Seguir tasks.md en orden
2. Un archivo a la vez
3. Tests para cada módulo
4. Commits incrementales

### Reglas
- ✅ Seguir patrones existentes
- ✅ Tests obligatorios
- ❌ No saltarse el orden del plan
- ❌ No implementar todo de golpe

---

## Fase 5: PR (Pull Request)

### Proceso
```bash
git add [archivos relevantes]
git commit -m "Implement FEAT-XXX: Nombre"
git push -u origin feature/XXX-nombre
gh pr create --title "FEAT-XXX: Nombre" --body "..." --base main
```

---

## Fase 6: MERGE (Cierre)

### Proceso

1. Review del PR
2. Aprobar y Merge
3. Actualizar `docs/features/FEAT-XXX/status.md` → 🟢 Complete
4. Actualizar `docs/features/_index.md`
5. Borrar rama local

---

## Checklist Rápido

```
□ INTERVIEW - spec.md completo
□ PLAN - design.md y tasks.md aprobados  
□ BRANCH - rama creada ANTES de codear
□ IMPLEMENT - tasks completadas, tests pasando
□ PR - creado con descripción completa
□ MERGE - documentación actualizada
```

---

## Anti-Patterns

| ❌ Anti-Pattern | ✅ Correcto |
|----------------|-------------|
| Codear sin interview | Interview primero |
| Codear sin rama | Rama antes de código |
| Codear sin plan | Plan primero |
| Commits gigantes | Commits incrementales |
| Ignorar tests | Tests obligatorios |

---
*Last updated: {date}*
'''

# Slash Commands

NEW_FEATURE_CMD = '''---
description: Create a new feature from template
argument-hint: FEAT-XXX-name
allowed-tools: Bash(mkdir:*), Bash(cp:*), Write, Read
---

# Create New Feature

## Instructions

1. Parse the argument to get feature ID and name
   - Example: `FEAT-001-auth` → ID=001, name=auth

2. Create feature directory:
   ```bash
   mkdir -p docs/features/FEAT-{ID}-{name}
   ```

3. Copy all files from template:
   ```bash
   cp docs/features/_template/* docs/features/FEAT-{ID}-{name}/
   ```

4. Update each file:
   - Replace `FEAT-XXX` with actual ID
   - Replace `[Feature Name]` with actual name
   - Set creation date

5. Update `docs/features/_index.md`:
   - Add new row to features table

6. Report what was created

## Argument
$ARGUMENTS
'''

INTERVIEW_CMD = '''---
description: Start interview process for a feature
argument-hint: FEAT-XXX
allowed-tools: Read, Write
---

# Interview Process

## Instructions

1. Read `docs/features/$ARGUMENTS/spec.md`

2. If spec.md is still template:
   - Start asking structured questions
   - Max 3-4 questions per turn
   - Provide suggested options for each
   - Update spec.md with each decision

3. If spec.md is already filled:
   - Review and ask if anything needs changes
   - Suggest moving to Plan phase

## Questions to Cover

- User stories and acceptance criteria
- UI/UX decisions
- Technical constraints
- Edge cases
- Error handling
- Security requirements
- Performance requirements

## Output Format

Update spec.md with decisions in table format:

| Decisión | Valor | Notas |
|----------|-------|-------|
| [topic] | [choice] | [why] |

## Argument
$ARGUMENTS
'''

PLAN_CMD = '''---
description: Create implementation plan for a feature
argument-hint: FEAT-XXX
allowed-tools: Read, Write, Bash(find:*), Bash(grep:*)
---

# Plan Implementation

## Instructions

1. Read feature spec:
   - `docs/features/$ARGUMENTS/spec.md`

2. Explore codebase:
   - Identify relevant existing files
   - Detect patterns to follow
   - Find dependencies

3. Create design document:
   - Update `docs/features/$ARGUMENTS/design.md`
   - List files to create/modify
   - Define data models
   - Define API endpoints
   - Add sequence diagrams if needed

4. Create task list:
   - Update `docs/features/$ARGUMENTS/tasks.md`
   - Order tasks by dependency
   - Group by: Backend, Frontend, Tests, Docs

5. Ask user to approve before implementation

## Do NOT
- Write any actual code
- Create any source files
- Modify anything outside docs/

## Argument
$ARGUMENTS
'''

IMPLEMENT_CMD = '''---
description: Start implementation of a feature
argument-hint: FEAT-XXX
allowed-tools: Read, Write, Edit, Bash(git:*), Bash(pytest:*), Bash(python:*)
---

# Implement Feature

## Pre-flight Checks

1. Verify branch exists:
   ```bash
   git branch --show-current
   ```
   - If on main/master → Create branch first!
   - Expected: `feature/XXX-name`

2. Verify plan is approved:
   - Read `docs/features/$ARGUMENTS/design.md`
   - Read `docs/features/$ARGUMENTS/tasks.md`

## Implementation Process

1. Update status:
   - Set `docs/features/$ARGUMENTS/status.md` to 🟡 In Progress

2. Follow tasks.md in order:
   - Mark each task as you start/complete
   - One file at a time
   - Run tests after each module

3. Commit incrementally:
   ```bash
   git add [files]
   git commit -m "FEAT-XXX: [what was done]"
   ```

## Completion

When all tasks done:
1. Run full test suite
2. Update status.md with completion
3. Suggest creating PR

## Argument
$ARGUMENTS
'''

SETTINGS_JSON = '''{
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Bash(git:*)",
      "Bash(pytest:*)",
      "Bash(python:*)",
      "Bash(pip:*)",
      "Bash(mkdir:*)",
      "Bash(cp:*)",
      "Bash(cat:*)",
      "Bash(ls:*)",
      "Bash(find:*)",
      "Bash(grep:*)"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(sudo:*)"
    ]
  }
}
'''


# =============================================================================
# MAIN LOGIC
# =============================================================================

def create_structure(project_name: str, description: str = "", stack: str = ""):
    """Create the complete project structure."""
    
    base_path = Path.cwd()
    date = datetime.now().strftime("%Y-%m-%d")
    
    if not description:
        description = f"{project_name} - A new project"
    
    if not stack:
        stack = "Python, FastAPI, PostgreSQL, Docker"
    
    # Template variables
    vars = {
        "project_name": project_name,
        "description": description,
        "stack": stack,
        "date": date,
        "total": "15"  # Default task count
    }
    
    # Directory structure
    dirs = [
        ".claude/commands",
        ".claude/skills/project-init/tools",
        "docs/architecture",
        "docs/features/_template",
        "docs/sprints",
        "docs/decisions",
        "src",
        "tests",
    ]
    
    # Files to create: (path, content_template)
    files = [
        ("CLAUDE.md", CLAUDE_MD),
        ("README.md", README_MD),
        ("docs/project.md", PROJECT_MD),
        ("docs/feature_cycle.md", FEATURE_CYCLE_MD),
        ("docs/features/_index.md", FEATURES_INDEX_MD),
        ("docs/features/_template/spec.md", FEATURE_SPEC_MD),
        ("docs/features/_template/design.md", FEATURE_DESIGN_MD),
        ("docs/features/_template/tasks.md", FEATURE_TASKS_MD),
        ("docs/features/_template/tests.md", FEATURE_TESTS_MD),
        ("docs/features/_template/status.md", FEATURE_STATUS_MD),
        ("docs/architecture/_index.md", ARCHITECTURE_INDEX_MD),
        ("docs/sprints/_index.md", SPRINTS_INDEX_MD),
        ("docs/decisions/_index.md", DECISIONS_INDEX_MD),
        (".claude/commands/new-feature.md", NEW_FEATURE_CMD),
        (".claude/commands/interview.md", INTERVIEW_CMD),
        (".claude/commands/plan.md", PLAN_CMD),
        (".claude/commands/implement.md", IMPLEMENT_CMD),
        (".claude/settings.json", SETTINGS_JSON),
        ("src/.gitkeep", ""),
        ("tests/.gitkeep", ""),
    ]
    
    created_files = []
    
    # Create directories
    for dir_path in dirs:
        full_path = base_path / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created: {dir_path}/")
    
    # Create files
    for file_path, template in files:
        full_path = base_path / file_path
        content = template.format(**vars) if template else ""
        full_path.write_text(content, encoding="utf-8")
        created_files.append(file_path)
        print(f"📄 Created: {file_path}")
    
    print(f"\n✅ Project structure created successfully!")
    print(f"   Total: {len(dirs)} directories, {len(created_files)} files")
    print(f"\n🚀 Next steps:")
    print(f"   1. Edit docs/project.md to define your project")
    print(f"   2. Run: /new-feature FEAT-001-nombre")
    print(f"   3. Follow docs/feature_cycle.md")
    
    return created_files


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        project_name = sys.argv[1]
        description = sys.argv[2] if len(sys.argv) > 2 else ""
        stack = sys.argv[3] if len(sys.argv) > 3 else ""
        create_structure(project_name, description, stack)
    else:
        print("Usage: python create_structure.py 'ProjectName' 'Description' 'Stack'")
        print("\nInteractive mode:")
        project_name = input("Project name: ").strip()
        description = input("Description (optional): ").strip()
        stack = input("Stack (optional, default: Python, FastAPI): ").strip()
        
        if project_name:
            create_structure(project_name, description, stack)
        else:
            print("❌ Project name is required")
