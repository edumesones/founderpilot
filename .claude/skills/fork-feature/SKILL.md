---
name: Fork Feature Skill
description: Fork terminal with git worktree isolation for parallel development. Use when user says 'fork feature', 'parallel work on feature', 'split feature tasks', or runs /fork-feature command.
---

# Fork Feature Skill

## Purpose

Launch **isolated parallel Claude Code sessions** using **git worktrees** for zero-conflict development. Each fork:
- Gets its own **physical directory** (worktree)
- Works on the **same branch** but in isolation
- Has **full feature context** (spec, design, tasks)
- Can work **simultaneously** without conflicts

## When to Use

- User wants to work on backend and frontend in parallel
- Feature has independent tasks that can be done simultaneously
- User says "fork", "parallel", "split tasks", "work on backend/frontend separately"

## Available Roles

| Role | Focus Area | Tasks Section |
|------|------------|---------------|
| `backend` | FastAPI, models, services | Backend section |
| `frontend` | React, Gradio, UI | Frontend section |
| `data` | Pipelines, ML, processing | Data section |
| `tests` | Unit, integration, e2e | Tests section |
| `docs` | README, docstrings | Documentation section |
| `full` | Everything in order | ALL sections |

## Instructions

### Standard Fork

When user requests a fork:

1. **Parse the request**:
   - Feature ID: `FEAT-XXX-name`
   - Role: `backend`, `frontend`, `tests`, etc.

2. **Validate feature exists**:
   ```bash
   ls docs/features/{feature_id}/
   ```

3. **Execute fork**:
   ```bash
   python .claude/skills/fork-feature/tools/fork_feature.py {feature_id} {role}
   ```

4. **Guide the user**:
   - New terminal opens
   - Tell them to paste the startup command

### What the Fork Receives

Each fork gets a context file (`.claude/contexts/{feature}_{role}.md`) containing:

1. **Feature Context**:
   - Full spec.md
   - Full design.md
   - Full tasks.md
   - Current status.md

2. **Role Instructions**:
   - What section to work on
   - Files they can modify
   - Files they should NOT touch

3. **Documentation Rules**:
   - Update tasks.md before/after each task
   - Commit after each task
   - Push every 30 minutes

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ Terminal Principal (Orquestador)                                │
│                                                                 │
│  1. User: "/fork-feature FEAT-001-auth backend"                │
│  2. Claude: Executes fork script                                │
│  3. New terminal opens                                          │
│  4. User goes to new terminal and starts working               │
│                                                                 │
│  Meanwhile, in principal terminal:                              │
│  5. User: "/fork-feature FEAT-001-auth frontend"               │
│  6. Another terminal opens for frontend                         │
│                                                                 │
│  Result: 3 terminals working on same feature                   │
│  - Terminal 1: Orchestration, review                           │
│  - Terminal 2: Backend tasks                                   │
│  - Terminal 3: Frontend tasks                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Sync Strategy

All forks work on the **same Git branch**. To avoid conflicts:

1. Each fork only modifies files in its domain
2. tasks.md: Each fork only updates its OWN section
3. Frequent commits and pushes
4. If conflict → merge carefully (tasks.md most likely)

## Example Usage

```
# User in main terminal
"Fork feature FEAT-001-auth for backend work"
→ /fork-feature FEAT-001-auth backend

"Also start frontend in parallel"  
→ /fork-feature FEAT-001-auth frontend

"I'll handle tests myself later"
→ Continue in main terminal
```

## Troubleshooting

### Fork script not found
```bash
python .claude/skills/fork-feature/tools/fork_feature.py --help
```
If not found, create the tools directory.

### Feature not found
Create the feature first:
```
/new-feature FEAT-XXX-name
```

### Terminal doesn't open
Manual fork:
1. Open new terminal manually
2. `cd /path/to/project`
3. `claude --dangerously-skip-permissions`
4. Read the context file and start working
