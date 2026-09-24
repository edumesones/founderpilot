---
description: Execute Phase 7 (Wrap-Up) - Close feature context, document learnings, clean temporaries
argument-hint: FEAT-XXX
allowed-tools: Read, Write, Bash(git:*), Bash(ls:*), Bash(rm:*)
---

# Wrap-Up Feature (Phase 7)

## Purpose

Close the feature cycle properly:
1. Create final summary in `context/wrap_up.md`
2. Document learnings and tech debt
3. Clean temporary context files
4. Update global docs if needed

## ⚠️ CRITICAL RULE
```
╔═══════════════════════════════════════════════════════════════╗
║  NO FEATURE IS COMPLETE WITHOUT WRAP-UP                       ║
║  Knowledge captured now is lost forever if not documented     ║
╚═══════════════════════════════════════════════════════════════╝
```

## Prerequisites

- Feature must be MERGED (status.md shows 🟢 Complete)
- If not merged yet: "Feature not merged. Complete PR first."

## Instructions

### 1. Verify Feature Status

```bash
cat docs/features/$ARGUMENTS/status.md
```

Check that:
- Status: 🟢 Complete
- Phase: Merge ✅

### 2. Gather Metrics

```bash
# Count files changed
git log --oneline --name-only main..HEAD 2>/dev/null | grep -v "^[a-f0-9]" | sort -u | wc -l

# Count commits
git log --oneline main..HEAD 2>/dev/null | wc -l

# Get PR number from status.md
grep -i "PR:" docs/features/$ARGUMENTS/status.md
```

### 3. Complete wrap_up.md

Read and complete `docs/features/$ARGUMENTS/context/wrap_up.md`:

**Required sections:**
- [ ] Metadata (dates, PR, branch)
- [ ] Executive Summary (2-3 sentences)
- [ ] Metrics (tasks, files, lines, tests)
- [ ] Key Decisions (from decisions.md)
- [ ] Tech Debt Created (if any)
- [ ] Learnings (what worked, what to improve)
- [ ] Timeline

### 4. Ask User for Learnings

```
"Before closing FEAT-XXX, let me ask:

1. ¿Qué funcionó bien en esta feature?
2. ¿Qué mejorarías para la próxima?
3. ¿Hay algún patrón reutilizable que identificaste?
4. ¿Quedó deuda técnica? ¿Cuál?"
```

Document answers in wrap_up.md.

### 5. Clean Temporary Files

```bash
# List MCP outputs for this feature
ls -la .claude/context/mcp/FEAT-XXX_* 2>/dev/null

# Ask user: "¿Eliminar estos archivos temporales?"
# If yes:
rm .claude/context/mcp/$ARGUMENTS_* 2>/dev/null
```

### 6. Check if Global Docs Need Update

Ask user:
```
"¿Hay algo de esta feature que deba añadirse a:
- CLAUDE.md (nuevas reglas)?
- README.md (nueva funcionalidad)?
- docs/patterns.md (patrones reutilizables)?"
```

If yes, make the updates.

### 7. Final Session Log Entry

Add to `context/session_log.md`:

```markdown
### [YYYY-MM-DD HH:MM] - Wrap-Up Complete ✅

**Fase:** Wrap-Up → Complete
**Feature:** FEAT-XXX officially closed

**Summary:**
- Total time: X days
- Tasks completed: X/Y
- Tech debt items: Z
- Learnings documented: ✅

**Global docs updated:**
- [List if any]

**Feature Status:** 🟢 Complete + Wrapped ✅
```

### 8. Update Status

Update `docs/features/$ARGUMENTS/status.md`:
- Add: `Wrap-up: ✅ YYYY-MM-DD`

### 9. Final Commit

```bash
git add docs/features/$ARGUMENTS/context/
git add docs/features/$ARGUMENTS/status.md
git commit -m "FEAT-XXX: Add wrap-up documentation"
git push
```

### 10. Completion Message

```
✅ FEAT-XXX Wrap-Up Complete!

Documented:
- context/wrap_up.md (final summary)
- context/session_log.md (closure entry)
- status.md (wrap-up timestamp)

Cleaned:
- [X temporary files removed]

Updated (if any):
- [Global docs]

Feature FEAT-XXX is now officially closed. 🎉
```

## Argument
$ARGUMENTS
