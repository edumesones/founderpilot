---
name: status-reporter
description: CORE SKILL - Must be called by ALL other skills to update project status. Maintains global project state, feature progress, and action log. Triggers on "Show status", "Project status", "What's the status".
globs: ["docs/features/**", "docs/status-log.md", "docs/project-status.md"]
---

# Status Reporter (CORE SYSTEM SKILL)

**THIS SKILL MUST BE INTEGRATED INTO ALL OTHER SKILLS.**

Every skill that modifies project state must call status-reporter functions to maintain consistent project status.

## Purpose

1. **Track global project status** in `docs/project-status.md`
2. **Track feature status** in `docs/features/_index.md`
3. **Track individual feature status** in `docs/features/FEAT-XXX/status.md`
4. **Maintain action log** in `docs/status-log.md`

## Files Managed

```
docs/
├── project-status.md      ← Global project dashboard
├── status-log.md          ← Chronological action log
└── features/
    ├── _index.md          ← All features dashboard
    └── FEAT-XXX/
        └── status.md      ← Individual feature status
```

## Integration Points

**EVERY skill must update status at these points:**

| Skill | When to Update | What to Update |
|-------|----------------|----------------|
| `project-interview` | After completing | project-status.md (Phase 0 progress) |
| `architecture-designer` | After each ADR | project-status.md (Phase 0 progress) |
| `mvp-planner` | After creating features | project-status.md, _index.md |
| `spec-architect` | After feature interview | FEAT-XXX/status.md, _index.md |
| `implementation-planner` | After generating plan | FEAT-XXX/status.md, _index.md |
| `implementer` | After EACH task | FEAT-XXX/status.md, _index.md, tasks.md |
| `fork-feature` | After creating fork | FEAT-XXX/status.md |
| `git-automator` | After PR/merge | FEAT-XXX/status.md, _index.md |

## Status Update Protocol

### 1. project-status.md (Global Dashboard)

```markdown
# Project Status Dashboard

## Last Updated
{timestamp}

## Phase 0: Project Setup
| Step | Status | Date |
|------|--------|------|
| Project Definition | ✅ | 2024-01-15 |
| Architecture | ✅ | 2024-01-15 |
| MVP Planning | ✅ | 2024-01-15 |

## MVP Progress
| Metric | Value |
|--------|-------|
| Total Features | 5 |
| Completed | 2 |
| In Progress | 1 |
| Pending | 2 |
| Progress | 40% |

## Active Work
| Feature | Phase | Progress | Assignee |
|---------|-------|----------|----------|
| FEAT-002 | Implement | 5/12 tasks | Terminal 1 |
| FEAT-003 | Implement | 8/10 tasks | Fork (worktree) |

## Recent Activity
- {timestamp}: FEAT-002 task 5 completed
- {timestamp}: FEAT-003 task 8 completed
- {timestamp}: FEAT-001 merged to main

## Blockers
| Feature | Issue | Since |
|---------|-------|-------|
| FEAT-004 | Waiting for API keys | 2024-01-14 |

## Timeline
```
Week 1: [████████░░] 80% - FEAT-001 ✅, FEAT-002 🟡
Week 2: [██░░░░░░░░] 20% - FEAT-003 🟡, FEAT-004 ⚪
Week 3: [░░░░░░░░░░] 0%  - FEAT-005 ⚪, Polish
```
```

### 2. features/_index.md (Features Dashboard)

```markdown
# Features Dashboard

## MVP Status

| ID | Feature | Status | Phase | Progress | Updated |
|----|---------|--------|-------|----------|---------|
| FEAT-001 | Auth | 🟢 Complete | Merged | 12/12 | 2024-01-14 |
| FEAT-002 | Upload | 🟡 In Progress | Implement | 5/12 | 2024-01-15 |
| FEAT-003 | AI Module | 🟡 In Progress | Implement | 8/10 | 2024-01-15 |
| FEAT-004 | Dashboard | 🔴 Blocked | Plan | - | 2024-01-14 |
| FEAT-005 | Export | ⚪ Pending | - | - | - |

## Status Legend
| Symbol | Meaning |
|--------|---------|
| ⚪ | Pending - Not started |
| 🟡 | In Progress - Active work |
| 🔵 | In Review - PR open |
| 🟢 | Complete - Merged |
| 🔴 | Blocked - Needs attention |
```

### 3. FEAT-XXX/status.md (Individual Feature)

```markdown
# FEAT-XXX Status

## Current State
- **Status:** 🟡 In Progress
- **Phase:** Implement
- **Progress:** 5/12 tasks (42%)
- **Branch:** feature/xxx-name
- **Assignee:** Main terminal

## Phase Progress
| Phase | Status | Date |
|-------|--------|------|
| Interview | ✅ | 2024-01-13 |
| Plan | ✅ | 2024-01-13 |
| Branch | ✅ | 2024-01-14 |
| Implement | 🟡 42% | - |
| PR | ⚪ | - |
| Merge | ⚪ | - |

## Task Progress
| Section | Done | Total | % |
|---------|------|-------|---|
| Backend | 3 | 6 | 50% |
| Frontend | 2 | 4 | 50% |
| Tests | 0 | 2 | 0% |

## Current Task
`[🟡] Implement UserService.update() method`

## Blockers
(none)

## Activity Log
- 2024-01-15 10:30: Task 5 completed
- 2024-01-15 10:15: Task 4 completed
- 2024-01-15 09:45: Task 3 completed
```

### 4. status-log.md (Chronological Log)

```markdown
# Project Activity Log

## 2024-01-15

### 10:30
- **Action:** Task completed
- **Feature:** FEAT-002
- **Task:** Implement UserService.update()
- **By:** Main terminal

### 10:15
- **Action:** Task completed
- **Feature:** FEAT-002
- **Task:** Implement UserService.create()
- **By:** Main terminal

### 09:00
- **Action:** Fork created
- **Feature:** FEAT-003
- **Worktree:** /project-FEAT-003-full
- **By:** Main terminal

## 2024-01-14

### 17:00
- **Action:** Feature merged
- **Feature:** FEAT-001
- **PR:** #23
- **By:** Main terminal
```

## Update Functions

**Skills should conceptually call these functions:**

### `update_task_complete(feature_id, task_description)`
1. Mark task as complete in tasks.md
2. Update progress table in tasks.md
3. Update FEAT-XXX/status.md progress
4. Update _index.md progress column
5. Update project-status.md active work
6. Append to status-log.md

### `update_phase_complete(feature_id, phase_name)`
1. Update FEAT-XXX/status.md phase table
2. Update _index.md phase column
3. Update project-status.md if all features in new phase
4. Append to status-log.md

### `update_blocker(feature_id, blocker_description)`
1. Update FEAT-XXX/status.md blockers
2. Update _index.md status to 🔴
3. Update project-status.md blockers section
4. Append to status-log.md

### `update_feature_complete(feature_id)`
1. Update FEAT-XXX/status.md to complete
2. Update _index.md status to 🟢
3. Update project-status.md MVP progress
4. Append to status-log.md

## Manual Status Check

User can ask:
- "Show status" → Display project-status.md summary
- "FEAT-XXX status" → Display feature status.md
- "What's in progress" → List active features
- "Show blockers" → List all blockers

## Consistency Rules

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  STATUS CONSISTENCY RULES                                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  1. NEVER complete an action without updating status                          ║
║     No orphan work - everything is tracked                                    ║
║                                                                                ║
║  2. Status updates are ATOMIC                                                  ║
║     Update ALL relevant files in one go                                       ║
║                                                                                ║
║  3. Timestamps are required                                                    ║
║     Every status change needs a timestamp                                     ║
║                                                                                ║
║  4. Progress must be calculable                                                ║
║     X/Y format, not vague "almost done"                                       ║
║                                                                                ║
║  5. Blockers are visible                                                       ║
║     Blocked status appears in ALL dashboards                                  ║
║                                                                                ║
║  6. Log is append-only                                                         ║
║     Never delete from status-log.md                                           ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

## Initial Setup

When project starts, create:

```bash
# Create status files if they don't exist
touch docs/project-status.md
touch docs/status-log.md
```

Initialize with templates above.
