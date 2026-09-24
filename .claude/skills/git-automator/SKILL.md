---
name: git-automator
description: Automates git workflow - sync, branch management, conflict resolution, smart commits, and PRs. Integrates with feature development cycle.
globs: ["*"]
---

# Git Automator (Feature Development Integration)

Automates the entire git workflow integrated with the feature development cycle.

## Prerequisites
- `git` and `gh` (GitHub CLI) installed

## Tool Detection & Setup

**BEFORE ANY OPERATION, detect and set up gh command:**

1. **Detect gh location:**
   ```bash
   gh --version 2>/dev/null
   ```

2. **If gh not found in PATH, try common locations:**
   - **Windows:** `"/c/Program Files/GitHub CLI/gh"` or `"C:\Program Files\GitHub CLI\gh.exe"`
   - **macOS:** `/usr/local/bin/gh` or `/opt/homebrew/bin/gh`
   - **Linux:** `/usr/bin/gh` or `/usr/local/bin/gh`

3. **Set GH_CMD variable:**
   - If `gh` works: `GH_CMD="gh"`
   - If full path needed: `GH_CMD="/c/Program Files/GitHub CLI/gh"`
   - If not found: Skip gh-dependent operations, provide manual URLs

4. **Test gh authentication:**
   ```bash
   $GH_CMD auth status
   ```

## Integration with Feature Cycle

### Phase 3: BRANCH
```bash
# Check current branch
git branch --show-current

# If on main/master, create feature branch
git checkout main
git pull origin main
git checkout -b feature/XXX-name
```

### Phase 4: IMPLEMENT (Commit Workflow)

**For each completed task:**

```bash
# 1. Check status
git status

# 2. Stage changes
git add [specific files for this task]

# 3. Commit with feature prefix
git commit -m "FEAT-XXX: Complete Task N - description"

# 4. Every 30 min or 3 tasks: push
git push origin feature/XXX-name
```

### Phase 5: PR Creation

```bash
# Push final changes
git push -u origin HEAD

# Create PR (if gh available)
$GH_CMD pr create \
  --title "FEAT-XXX: Feature Name" \
  --body "## Summary
- [Summary of changes]

## Features
- [x] Feature 1
- [x] Feature 2

## Tests
- X tests passing

## Checklist
- [x] Tests passing
- [x] Docs updated" \
  --base main

# If gh not available, provide URL:
# https://github.com/[user]/[repo]/compare/feature/XXX-name
```

## Conflict Resolution Protocol

**IF CONFLICTS OCCUR:**

1. **Identify conflicts:**
   ```bash
   git status
   ```

2. **Inform user:**
   "Conflicts detected in: [list files]"

3. **Offer assistance:**
   "Do you want me to read these files and help you choose which version to keep?"

4. **WAIT for user instruction** on each file

5. **Resolve and continue:**
   ```bash
   # After user resolves
   git add [resolved_file]
   
   # When all resolved
   git rebase --continue
   ```

## Smart Commit Messages

### Format
```
FEAT-XXX: [Action] [Component] - [Brief description]
```

### Examples
```
FEAT-001: Add User model with validation
FEAT-001: Create auth service with JWT support
FEAT-001: Add login endpoint and tests
FEAT-002: Fix dashboard layout on mobile
```

### Rules
- Keep under 72 characters
- Start with feature ID
- Use present tense ("Add" not "Added")
- NO emojis unless user requests
- NO automatic co-author tags

## Worktree-Specific Git Operations

When working in a worktree (fork):

```bash
# Verify you're in worktree
git worktree list

# You're already on the feature branch
git branch --show-current  # Should show feature/XXX-name

# Commits work normally
git add .
git commit -m "FEAT-XXX: description"

# Push to remote
git push -u origin feature/XXX-name

# Create PR from worktree
$GH_CMD pr create --fill --base main
```

## Sync Operations

### Before starting work (main repo)
```bash
git fetch origin
git checkout main
git pull origin main
```

### Keep feature branch updated
```bash
# From feature branch
git fetch origin
git rebase origin/main

# If conflicts, follow Conflict Resolution Protocol
```

### After PR merge (cleanup)
```bash
# Back in main repo
git checkout main
git pull origin main
git branch -d feature/XXX-name  # Delete local branch

# If using worktree
git worktree remove ../project-FEAT-XXX-full
```

## Removing Files from Tracking

If files were accidentally committed:

```bash
# Remove from tracking (keep local)
git rm --cached .env
git rm --cached -r .claude/contexts/

# Commit the removal
git commit -m "Remove sensitive files from tracking"

# Ensure .gitignore is updated
echo ".env" >> .gitignore
echo ".claude/contexts/" >> .gitignore
```

## Error Handling

| Error | Solution |
|-------|----------|
| `gh: command not found` | Try full path or skip gh operations |
| `not authenticated` | Run `gh auth login` |
| `branch already exists` | Use existing or create new name |
| `merge conflict` | Follow Conflict Resolution Protocol |
| `push rejected` | Pull/rebase first, then push |

## Quick Reference

```bash
# Start feature
git checkout -b feature/XXX-name

# During implementation
git add [files]
git commit -m "FEAT-XXX: description"
git push origin feature/XXX-name

# Create PR
gh pr create --fill --base main

# After merge
git checkout main
git pull
git branch -d feature/XXX-name
```
