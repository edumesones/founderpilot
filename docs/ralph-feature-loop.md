# Ralph Feature Loop - Autonomous Development System

## Overview

Ralph Loop is an autonomous development system that executes the complete 7-phase Feature Development Cycle with minimal human intervention.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RALPH LOOP                                          │
│                    Autonomous Feature Development                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Human defines features → Ralph builds them → Human approves PRs               │
│                                                                                  │
│   ┌─────────┐     ┌─────────────────────────────────────┐     ┌─────────┐       │
│   │ _index  │ ──► │         RALPH ORCHESTRATOR          │ ──► │ Merged  │       │
│   │   .md   │     │                                     │     │ Features│       │
│   │⚪Pending│     │  Creates worktrees, monitors, cleans│     │🟢Complete│      │
│   └─────────┘     └─────────────────────────────────────┘     └─────────┘       │
│                                  │                                               │
│                    ┌─────────────┼─────────────┐                                │
│                    ▼             ▼             ▼                                │
│              ┌──────────┐  ┌──────────┐  ┌──────────┐                           │
│              │ FEAT-001 │  │ FEAT-002 │  │ FEAT-003 │                           │
│              │   Loop   │  │   Loop   │  │   Loop   │                           │
│              │(worktree)│  │(worktree)│  │(worktree)│                           │
│              └──────────┘  └──────────┘  └──────────┘                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Prerequisites

```bash
# Required tools
git --version        # Git installed
gh --version         # GitHub CLI installed and authenticated
claude --version     # Claude CLI available
python3 --version    # Python 3 for JSON manipulation

# Authenticate GitHub CLI if needed
gh auth login
```

### 2. Setup

```bash
# Make scripts executable
chmod +x ralph-orchestrator.sh ralph-feature.sh

# Ensure _index.md exists with features
cat docs/features/_index.md
```

### 3. Add Features to Process

Edit `docs/features/_index.md`:

```markdown
| ID | Feature | Status | Phase | Progress | Priority | Updated |
|----|---------|--------|-------|----------|----------|---------|
| FEAT-001-auth | User Auth | ⚪ Pending | - | - | P0 | 2025-01-23 |
| FEAT-002-api | REST API | ⚪ Pending | - | - | P0 | 2025-01-23 |
```

Create feature folders:
```bash
mkdir -p docs/features/FEAT-001-auth/context
cp docs/features/_template/* docs/features/FEAT-001-auth/
```

### 4. Run

```bash
# Process all pending features (max 3 in parallel)
./ralph-orchestrator.sh 3

# Or run single feature
./ralph-feature.sh FEAT-001-auth
```

---

## How It Works

### The 7-Phase Cycle

Ralph executes each phase of the Feature Development Cycle:

| Phase | What Happens | Human Input? |
|-------|-------------|--------------|
| **1. Interview** | Reads/completes spec.md | Only if TBD values |
| **2. Plan** | Generates design.md + tasks.md | No |
| **3. Branch** | Creates git branch | No |
| **4. Implement** | Executes tasks, commits code | No |
| **5. PR** | Creates pull request | No |
| **6. Merge** | Waits for approval | **YES - Review PR** |
| **7. Wrap-Up** | Creates wrap_up.md, documents | No |

### Phase Detection

Ralph automatically detects the current phase by checking:

```python
if spec.md has all decisions filled:
    if design.md and tasks.md exist:
        if branch exists:
            if all tasks [x] complete:
                if PR exists:
                    if PR merged:
                        if wrap_up.md complete:
                            → COMPLETE
                        else:
                            → WRAPUP
                    else:
                        → MERGE (waiting)
                else:
                    → PR
            else:
                → IMPLEMENT
        else:
            → BRANCH
    else:
        → PLAN
else:
    → INTERVIEW
```

### Iteration Model

Each loop iteration = one phase action:

```
Iteration 1:  Interview phase
Iteration 2:  Plan phase  
Iteration 3:  Branch phase
Iteration 4:  Implement (3 tasks)
Iteration 5:  Implement (3 tasks)
Iteration 6:  Implement (3 tasks)
Iteration 7:  Implement (remaining tasks)
Iteration 8:  PR phase
Iteration 9:  Merge (waiting...)
Iteration 10: Merge (waiting...)
Iteration 11: Merge (approved!)
Iteration 12: Wrap-up phase
→ COMPLETE
```

---

## Commands

### Orchestrator

```bash
# Start with default 3 parallel
./ralph-orchestrator.sh

# Custom parallel limit
./ralph-orchestrator.sh 5

# Check status
./ralph-orchestrator.sh --status

# Stop all loops
./ralph-orchestrator.sh --stop
```

### Single Feature

```bash
# Run with default 15 iterations
./ralph-feature.sh FEAT-001-auth

# Custom iteration limit
./ralph-feature.sh FEAT-001-auth 20
```

### Via Claude Command

```bash
/ralph orchestrator 3
/ralph feature FEAT-001-auth
/ralph status
/ralph stop
```

---

## Pause Conditions

Ralph pauses (doesn't crash) in these situations:

### 1. Human Input Needed (Interview)

**When:** spec.md has TBD values that can't be auto-filled

**What to do:**
1. Edit `docs/features/FEAT-XXX/spec.md`
2. Fill in Technical Decisions table
3. Run `/ralph feature FEAT-XXX` to resume

### 2. Waiting for Merge Approval

**When:** PR created, needs human review

**What to do:**
1. Review PR in GitHub
2. Approve and merge
3. Ralph will detect and continue to wrap-up

### 3. Too Many Failures (3 consecutive)

**When:** Something is broken

**What to do:**
1. Check `ralph-FEAT-XXX.log` in worktree
2. Check `docs/features/FEAT-XXX/context/session_log.md`
3. Fix the issue
4. Run `/ralph feature FEAT-XXX` to resume

---

## State Files

### feature-loop-state.json

Tracks all loop states:

```json
{
    "orchestrator": {
        "status": "running",
        "started_at": "2025-01-23T14:00:00",
        "max_parallel": 3,
        "pid": 12345
    },
    "features": {
        "FEAT-001-auth": {
            "status": "running",
            "phase": "implement",
            "iterations": 5,
            "failures": 0,
            "worktree": "../project-FEAT-001-loop",
            "pid": 12346
        }
    },
    "completed": [],
    "failed": []
}
```

### activity.md

Human-readable log:

```markdown
- **[2025-01-23 14:00:00]** 🎭 **Orchestrator started** (max parallel: 3)
- **[2025-01-23 14:01:00]** 🚀 Started loop for **FEAT-001-auth**
- **[2025-01-23 14:30:00]** ✅ **FEAT-001-auth** Implementation Complete
```

---

## Integration with Existing Workflow

Ralph Loop integrates seamlessly with your existing Feature Development Cycle:

| Manual Command | Ralph Equivalent |
|----------------|------------------|
| `/interview FEAT-XXX` | Auto-executed in Interview phase |
| `/plan FEAT-XXX` | Auto-executed in Plan phase |
| `git checkout -b feature/...` | Auto-executed in Branch phase |
| `/git "message"` | Auto-commit after each task |
| `/git pr` | Auto-executed in PR phase |
| `/wrap-up FEAT-XXX` | Auto-executed in Wrap-up phase |
| `/resume FEAT-XXX` | Run `/ralph feature FEAT-XXX` |

### Using Both

You can mix manual and autonomous work:

```bash
# Start a feature manually
/interview FEAT-001-auth
# Complete the interview with human decisions

# Let Ralph continue from there
./ralph-feature.sh FEAT-001-auth
# Ralph detects Interview complete, continues with Plan
```

---

## Worktree Isolation

Each feature runs in its own git worktree:

```
proyecto/                           ← Main repo
proyecto-FEAT-001-auth-loop/        ← Worktree for FEAT-001
proyecto-FEAT-002-api-loop/         ← Worktree for FEAT-002
proyecto-FEAT-003-dashboard-loop/   ← Worktree for FEAT-003
```

Benefits:
- **Zero conflicts** between parallel features
- **Independent branches** per feature
- **Clean state** for each loop
- **Automatic cleanup** after merge

---

## Troubleshooting

### "Feature directory not found"

```bash
# Create the feature folder
mkdir -p docs/features/FEAT-XXX-name/context
cp docs/features/_template/* docs/features/FEAT-XXX-name/
```

### "gh: command not found"

```bash
# Install GitHub CLI
# macOS
brew install gh

# Windows
winget install GitHub.cli

# Authenticate
gh auth login
```

### "Branch already exists"

```bash
# Ralph will use existing branch
# Or delete and recreate:
git branch -D feature/xxx-name
```

### Loop stuck on merge

```bash
# Check PR status
gh pr view

# Manually merge if needed
gh pr merge --merge
```

### Check what went wrong

```bash
# View feature log
cat proyecto-FEAT-XXX-loop/ralph-FEAT-XXX.log

# View session log
cat docs/features/FEAT-XXX/context/session_log.md

# View state
cat feature-loop-state.json
```

---

## Best Practices

### 1. Prepare Good Specs

The better your spec.md, the better Ralph performs:

```markdown
## Technical Decisions

| # | Area | Question | Decision | Notes |
|---|------|----------|----------|-------|
| 1 | Auth | Session storage | JWT + Redis | 24h expiry |
| 2 | API | Response format | JSON envelope | Standard structure |
```

Avoid TBD values - fill them with sensible defaults.

### 2. Review Commits

Ralph commits frequently. Review the commit history:

```bash
git log --oneline -20
```

### 3. Monitor Progress

Check the activity log:

```bash
tail -50 activity.md
```

### 4. Don't Modify Running Features

If Ralph is working on a feature:
- Don't edit the same files manually
- Don't push to the same branch
- Wait for Ralph to pause or complete

### 5. Clean Up Old Worktrees

After features are merged:

```bash
# Orchestrator cleans automatically, but if needed:
git worktree list
git worktree remove ../proyecto-FEAT-XXX-loop --force
```

---

## Architecture Details

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FILE STRUCTURE                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   proyecto/                                                                      │
│   ├── ralph-orchestrator.sh      # Multi-feature orchestrator                   │
│   ├── ralph-feature.sh           # Single feature loop                          │
│   ├── feature-loop-state.json    # State tracking                               │
│   ├── activity.md                # Activity log                                 │
│   │                                                                              │
│   ├── .claude/                                                                   │
│   │   ├── commands/                                                              │
│   │   │   └── ralph.md           # /ralph command                               │
│   │   └── skills/                                                                │
│   │       └── ralph-loop/                                                        │
│   │           └── SKILL.md       # Skill documentation                          │
│   │                                                                              │
│   └── docs/                                                                      │
│       ├── features/                                                              │
│       │   ├── _index.md          # Feature dashboard (Ralph reads this)         │
│       │   ├── _template/         # Templates for new features                   │
│       │   └── FEAT-XXX/          # Feature folders                              │
│       │       ├── spec.md                                                        │
│       │       ├── design.md                                                      │
│       │       ├── tasks.md                                                       │
│       │       ├── status.md                                                      │
│       │       └── context/                                                       │
│       │           ├── session_log.md                                             │
│       │           ├── decisions.md                                               │
│       │           ├── blockers.md                                                │
│       │           └── wrap_up.md                                                 │
│       │                                                                          │
│       ├── feature_cycle.md       # 7-phase cycle documentation                  │
│       └── ralph-feature-loop.md  # This file                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Version History

- **v1.0** - Initial release
  - 7-phase autonomous execution
  - Git worktree isolation
  - Orchestrator for parallel features
  - Integration with Feature Development Cycle v2.0

---

*Last updated: 2025-01-23*
