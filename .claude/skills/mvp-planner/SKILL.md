---
name: mvp-planner
description: Define and prioritize MVP features. Triggers on "Define MVP features", "Help me plan the MVP", "What features for MVP", "Let's define the features".
globs: ["docs/project.md", "docs/features/**"]
---

# MVP Planner (Fase 0)

Transform project vision into concrete, prioritized features ready for implementation.

## Triggers

- "Define MVP features"
- "Help me plan the MVP"
- "What features should we build?"
- "Let's define the features"
- "Plan the MVP"
- `/mvp`

## Prerequisites

- `docs/project.md` should exist
- `docs/architecture/_index.md` ideally exists
- If not: "Let's first define the project and architecture"

## Purpose

Create:
1. **Prioritized feature list** in `docs/features/_index.md`
2. **Feature folders** for top 3-5 MVP features
3. **Clear scope** of what's in/out of MVP

## Process

### 1. Read Context

```bash
# Read project definition
cat docs/project.md

# Read architecture (if exists)
cat docs/architecture/_index.md 2>/dev/null

# Check existing features
ls -la docs/features/ 2>/dev/null
```

### 2. Extract Core Value

From project.md, identify:
- What's the ONE thing that makes this valuable?
- What's the minimum a user needs to get value?
- What can wait until v1.1?

### 3. Feature Brainstorm Interview

```
"Based on your project, I see these potential features:

CORE (likely MVP):
1. [Feature] - [Why it's core]
2. [Feature] - [Why it's core]
3. [Feature] - [Why it's core]

IMPORTANT (maybe MVP):
4. [Feature] - [Value add]
5. [Feature] - [Value add]

NICE TO HAVE (post-MVP):
6. [Feature] - [Can wait because...]
7. [Feature] - [Can wait because...]

Questions:
1. Did I miss any critical features?
2. Which of the 'important' ones are must-have for launch?
3. Anything in 'core' that could actually wait?"
```

### 4. Prioritization Framework

Use MoSCoW or similar:

| Priority | Meaning | MVP? |
|----------|---------|------|
| **Must** | Won't work without it | ✅ Yes |
| **Should** | Important but workaround exists | ⚠️ Maybe |
| **Could** | Nice to have | ❌ No |
| **Won't** | Explicitly out of scope | ❌ No |

### 5. Define Feature Scope

For each MVP feature, clarify:

```
Feature: User Authentication

MUST have (MVP):
- Email/password login
- Session management
- Logout

SHOULD have (MVP if time):
- Password reset
- Remember me

COULD have (post-MVP):
- OAuth (Google, GitHub)
- 2FA

WON'T have (out of scope):
- SSO/SAML
- Passwordless/magic link
```

### 6. Create Feature Folders

For each MVP feature, create structure:

```bash
# Using the new-feature command pattern
# Creates: docs/features/FEAT-001-auth/
#   - spec.md (template)
#   - design.md (template)
#   - tasks.md (template)
#   - status.md (template)
#   - tests.md (template)
```

### 7. Update Features Index

Create/update `docs/features/_index.md`:

```markdown
# Features Dashboard

## MVP Scope

**Target:** [Date or milestone]
**Total features:** X
**Status:** Planning

## Feature List

### 🎯 MVP (Must Have)

| ID | Feature | Status | Priority | Est. Effort |
|----|---------|--------|----------|-------------|
| FEAT-001 | [Auth](./FEAT-001-auth/) | ⚪ Pending | P0 | 3 days |
| FEAT-002 | [Core Flow](./FEAT-002-core/) | ⚪ Pending | P0 | 5 days |
| FEAT-003 | [Basic UI](./FEAT-003-ui/) | ⚪ Pending | P0 | 2 days |

### 📋 Post-MVP (Should Have)

| ID | Feature | Priority | Notes |
|----|---------|----------|-------|
| FEAT-004 | OAuth integration | P1 | After launch |
| FEAT-005 | Admin dashboard | P1 | When needed |

### 💭 Future (Could Have)

- API for third-party integrations
- Mobile app
- Team features

### 🚫 Out of Scope (Won't Have)

- Enterprise SSO
- Self-hosted option
- White-labeling

## MVP Timeline

```
Week 1: FEAT-001 (Auth) + FEAT-002 (Core)
Week 2: FEAT-003 (UI) + Integration
Week 3: Testing + Polish + Launch
```

## Dependencies

```
FEAT-001 (Auth) ─────┐
                     ├──▶ FEAT-003 (UI)
FEAT-002 (Core) ─────┘
```

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ⚪ | Pending |
| 🟡 | In Progress |
| 🔵 | In Review |
| 🟢 | Complete |
| 🔴 | Blocked |

---
*Last updated: {date}*
*MVP target: [date]*
```

### 8. Interview Rules

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  MVP PLANNING RULES                                                            ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  1. Ruthlessly cut scope                                                       ║
║     "Can you launch without this? Yes? → Post-MVP"                            ║
║                                                                                ║
║  2. Maximum 5 features for MVP                                                 ║
║     More than 5 = you're not building an MVP                                  ║
║                                                                                ║
║  3. Each feature must have clear "done" criteria                              ║
║     "User can X" not "Implement X"                                            ║
║                                                                                ║
║  4. Identify dependencies early                                                ║
║     Which features block others?                                              ║
║                                                                                ║
║  5. Time-box the MVP                                                           ║
║     "If it takes more than X weeks, we're doing too much"                     ║
║                                                                                ║
║  6. The first feature should prove the core value                             ║
║     Start with what makes this product unique                                 ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### 9. Create Feature Folders

After prioritization, create each MVP feature:

```
For each MVP feature:
1. Create folder: docs/features/FEAT-00X-name/
2. Copy templates from docs/features/_template/
3. Pre-fill spec.md with scope from this discussion
4. Update status.md to "Pending - Spec needed"
```

### 10. Completion Check

Before ending, verify:
- [ ] MVP features are limited (3-5 max)
- [ ] Each feature has clear scope (must/should/could/won't)
- [ ] Dependencies are identified
- [ ] Timeline is realistic
- [ ] Out of scope is explicit
- [ ] Feature folders created

### 11. Handoff

When complete:

```
✅ MVP planned. Created:
- docs/features/_index.md (dashboard)
- docs/features/FEAT-001-[name]/ (folder + templates)
- docs/features/FEAT-002-[name]/ (folder + templates)
- docs/features/FEAT-003-[name]/ (folder + templates)

Recommended order:
1. FEAT-001 - [name] (no dependencies)
2. FEAT-002 - [name] (depends on FEAT-001)
3. FEAT-003 - [name] (depends on FEAT-001, FEAT-002)

Next step:
"Interview me about FEAT-001-[name]" → Deep dive into first feature spec

Or: /interview FEAT-001-[name]
```

## Example Flow

```
User: "Define MVP features"

Claude: [Reads docs/project.md]

"Based on your dotfiles manager project, here's my feature breakdown:

🎯 CORE (Must have for MVP):
1. **Init/Setup** - Initialize dotfiles tracking in a directory
2. **Link** - Symlink dotfiles to home directory
3. **Sync** - Push/pull changes to git remote

📋 IMPORTANT (Should have):
4. **Profiles** - Different configs for work/home machines
5. **Diff** - Show what changed before sync

💭 NICE TO HAVE (Post-MVP):
6. **Secrets** - Encrypted sensitive files
7. **Plugins** - Custom hooks/scripts
8. **GUI** - Desktop app wrapper

Questions:
1. Can you launch with just init + link + sync?
2. Are profiles essential for your use case, or can that wait?
3. What's your target timeline?"

User: "Yes, init/link/sync is enough. Profiles can wait. 2 weeks."

Claude: "Perfect. MVP scope locked:

FEAT-001-init: Initialize dotfiles tracking
FEAT-002-link: Symlink management  
FEAT-003-sync: Git sync (push/pull)

Creating feature folders now..."

[Creates folders and updates _index.md]

"✅ Done. Start with: 'Interview me about FEAT-001-init'"
```
