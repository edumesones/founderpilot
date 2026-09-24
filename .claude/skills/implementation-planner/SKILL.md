---
name: implementation-planner
description: Generate technical design and tasks from feature spec. Triggers on "implement FEAT-XXX", "plan implementation for FEAT-XXX", "create implementation plan for FEAT-XXX". Works in Claude plan mode or normal mode.
globs: ["docs/features/**/spec.md", "docs/features/**/design.md", "docs/features/**/tasks.md", "docs/features/**/status.md"]
---

# Implementation Planner

Transform a feature specification into actionable technical design and tasks.

## Triggers

- "implement FEAT-XXX" (in plan mode or normal)
- "plan implementation for FEAT-XXX"
- "create implementation plan for FEAT-XXX"
- "generate tasks for FEAT-XXX"
- "create technical design for FEAT-XXX"

## Prerequisites

- Feature folder must exist: `docs/features/FEAT-XXX/`
- `spec.md` must be completed (interview done)
- If spec incomplete: "Let's first interview about this feature"

## Purpose

Create:
1. **design.md** - Technical architecture for the feature
2. **tasks.md** - Granular, actionable implementation tasks
3. Update **status.md** - Mark phase as "Plan ✅"

## Process

### 1. Read Context

```bash
# Read feature spec
cat docs/features/FEAT-XXX/spec.md

# Read project architecture for consistency
cat docs/architecture/_index.md 2>/dev/null

# Read project context
cat docs/project.md 2>/dev/null

# Check current status
cat docs/features/FEAT-XXX/status.md
```

### 2. Generate design.md

Based on spec.md, create technical design covering:

**Required sections:**
- Overview (brief technical approach)
- Architecture (ASCII diagram + components table)
- Data Model (models, relationships)
- API Design (endpoints, request/response examples)
- Service Layer (services, business logic)
- Error Handling (error cases, responses)
- Security Considerations
- Performance Considerations
- Dependencies (external + internal)
- File Structure (new files + modified files)
- Implementation Order

**Template structure:**

```markdown
# FEAT-XXX: [Feature Name] - Technical Design

## Overview
[2-3 sentences describing technical approach]

## Architecture

### System Context
```
[ASCII diagram]
```

### Components
| Component | Responsibility | Location |
|-----------|---------------|----------|
| ... | ... | `src/...` |

## Data Model

### New Models
```python
class ModelName(Base):
    # fields...
```

### Relationships
[Description or diagram]

## API Design

### Endpoints
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| ... | ... | ... | ... |

### Examples
```json
// Request/Response examples
```

## Service Layer
| Service | Methods | Dependencies |
|---------|---------|--------------|
| ... | ... | ... |

## Error Handling
| Error Case | HTTP Code | Response |
|------------|-----------|----------|
| ... | ... | ... |

## Security Considerations
- [Point 1]
- [Point 2]

## Performance Considerations
- [Point 1]
- [Point 2]

## Dependencies
- External: [libs/services needed]
- Internal: [other features this depends on]

## File Structure

### New Files
```
src/
├── [new files]
tests/
├── [new test files]
```

### Modified Files
```
[existing files to modify]
```

## Implementation Order
1. [First thing to build]
2. [Second thing]
3. [etc.]

---
*Generated: {date}*
*Status: Ready for implementation*
```

### 3. Generate tasks.md

Break design into granular, actionable tasks:

**Task rules:**
- Each task = 15-60 minutes of work
- Each task = ONE commit
- Tasks ordered by dependency
- Each task starts with a verb (Create, Add, Implement, Update, Test)
- Each task has clear "done" criteria

**Template structure:**

```markdown
# FEAT-XXX: [Feature Name] - Tasks

## Progress

| Section | Progress | Tasks |
|---------|----------|-------|
| Backend | ⬜ 0% | 0/X |
| Frontend | ⬜ 0% | 0/X |
| Tests | ⬜ 0% | 0/X |
| Docs | ⬜ 0% | 0/X |
| **Total** | ⬜ 0% | 0/X |

## Status Legend
- `[ ]` Pending
- `[🟡]` In Progress  
- `[x]` Complete
- `[🔴]` Blocked (reason)
- `[⏭️]` Skipped (reason)

---

## Backend Tasks

### Models & Database
- [ ] Create `Model` in `src/models/`
- [ ] Create migration
- [ ] Run and verify migration

### Schemas  
- [ ] Create request/response schemas
- [ ] Add validation rules

### Services
- [ ] Create service class
- [ ] Implement CRUD methods
- [ ] Add error handling

### API Routes
- [ ] Create router
- [ ] Implement endpoints
- [ ] Register router in app

---

## Frontend Tasks

### Components
- [ ] Create form component
- [ ] Create list component
- [ ] Create detail component

### Integration
- [ ] Add API client
- [ ] Add state management
- [ ] Handle loading/error states

---

## Tests

### Unit Tests
- [ ] Test service methods
- [ ] Test validation

### Integration Tests
- [ ] Test API endpoints
- [ ] Test error cases

---

## Documentation
- [ ] Add API docs
- [ ] Update README

---

## Blockers & Decisions

| Issue | Status | Resolution |
|-------|--------|------------|
| (none yet) | - | - |

---
*Generated: {date}*
*Total tasks: X*
*Estimated effort: X days*
```

### 4. Update status.md

**CRITICAL: Always update status after generating plan**

```markdown
# Update status.md with:

## Phase Progress
| Phase | Status | Date |
|-------|--------|------|
| Interview | ✅ Complete | {date} |
| Plan | ✅ Complete | {today} |  ← UPDATE THIS
| Branch | ⚪ Pending | - |
| Implement | ⚪ Pending | - |
| PR | ⚪ Pending | - |
| Merge | ⚪ Pending | - |

## Current Phase
**Plan** → Ready for Branch creation

## Generated Artifacts
- design.md ✅
- tasks.md ✅ (X tasks total)
```

### 5. Update Global Status

**CRITICAL: Update docs/features/_index.md**

```markdown
# In _index.md, update feature row:

| ID | Feature | Status | Phase |
|----|---------|--------|-------|
| FEAT-XXX | [Name] | 🟡 In Progress | Plan ✅ |  ← UPDATE
```

### 6. Completion Message

After generating plan:

```
✅ Implementation plan created for FEAT-XXX

Generated:
- docs/features/FEAT-XXX/design.md (technical design)
- docs/features/FEAT-XXX/tasks.md (X tasks)

Updated:
- docs/features/FEAT-XXX/status.md (Phase: Plan ✅)
- docs/features/_index.md (global status)

Next steps:
1. Create branch: git checkout -b feature/XXX-name
2. Start implementation: "Execute FEAT-XXX tasks"
   Or fork for parallel: /fork-feature FEAT-XXX full
```

## Integration with Status Reporter

**This skill MUST call status-reporter at the end:**

1. Update feature status.md
2. Update global _index.md  
3. Log action to docs/status-log.md (if exists)

See `status-reporter` skill for details.
