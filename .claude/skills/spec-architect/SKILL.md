---
name: spec-architect
description: Deep interview process to transform rough ideas into professional technical specifications. Forces exhaustive questioning before any implementation.
globs: ["*.md", "docs/features/**"]
---

# Spec Architect & Interviewer

This skill forces a deep interview process to clarify requirements before coding.

## When to Use

- User says "Interview me about FEAT-XXX"
- User runs `/interview FEAT-XXX`
- User has rough notes and wants professional spec
- Starting Phase 1 (INTERVIEW) of feature cycle

## The Interview Philosophy

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  "The spec is the contract. Ambiguity in the spec = bugs in the code."       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

Your job is to **eliminate ambiguity** by asking questions the user hasn't thought about.

## Interview Protocol

### 1. Read Context First

```bash
# Read the feature spec
cat docs/features/FEAT-XXX/spec.md

# Read project context
cat docs/project.md

# Read architecture constraints
cat docs/architecture/_index.md
```

### 2. Interview Categories

#### A. User Stories & Flows
- Who are the actors? (user types, roles, permissions)
- What's the happy path? Step by step.
- What are alternate paths?
- What triggers this feature? What's the entry point?

#### B. Technical Implementation
- Data models needed
- API endpoints (method, path, payload, response)
- State management approach
- External service integrations
- Database queries/operations

#### C. Edge Cases & Errors
- What if network fails?
- What if user submits invalid data?
- What if concurrent requests happen?
- What if dependent service is down?
- Rate limiting needs?

#### D. UI/UX Details
- What does user see in each state? (loading, empty, error, success)
- Form validation - when and how?
- Feedback mechanisms (toasts, modals, inline)
- Mobile considerations

#### E. Security & Performance
- Authentication required?
- Authorization rules?
- Input sanitization
- Sensitive data handling
- Expected load/performance requirements

#### F. Trade-offs
- Speed vs reliability?
- Simplicity vs flexibility?
- Build vs buy?
- Now vs later?

### 3. Question Quality Rules

```
❌ NEVER ASK:
- Obvious questions ("What color should the button be?")
- Yes/no questions without context
- Multiple unrelated questions at once

✅ ALWAYS ASK:
- Questions that reveal hidden complexity
- Questions with suggested options
- Questions about failure scenarios
- Follow-up questions that dig deeper
```

### 4. Answer Handling

**When user answers clearly:**
→ Document immediately in spec.md
→ Move to next question

**When user says "I don't know":**
→ Propose sensible default with reasoning
→ Document as "Recommended: X because Y"
→ Mark as "[Can revisit]" if user is unsure

**When user says "You decide":**
→ Make decision based on best practices
→ Document with full reasoning
→ User can override later

### 5. Documentation Format

Update spec.md with structured decisions:

```markdown
## Technical Decisions

| # | Area | Question | Decision | Rationale |
|---|------|----------|----------|-----------|
| 1 | Auth | Session duration | 24h + refresh token | Balance security/UX |
| 2 | Error | Failed login handling | 5 attempts → 15min lockout | Prevent brute force |
| 3 | API | Response format | JSON with envelope | Consistency with existing |
```

### 6. Completion Checklist

Before ending interview, verify:

- [ ] All user stories have acceptance criteria
- [ ] Happy path fully documented
- [ ] Error handling defined for each operation
- [ ] Security requirements specified
- [ ] Performance expectations set
- [ ] Dependencies identified
- [ ] Out of scope explicitly listed
- [ ] Open questions resolved or marked

### 7. Handoff

When interview complete:

1. Finalize spec.md with professional formatting
2. Update status.md → Phase: Interview ✅
3. Tell user: "Spec complete. Run `/plan implement FEAT-XXX` for technical design."

## Example Interview Flow

```
Claude: "Let's define FEAT-001-auth. First, walk me through the login flow 
        from the user's perspective - what do they see and do?"

User:   "They enter email and password, click login, go to dashboard."

Claude: "Got it. A few follow-ups:
        1. Is there a 'Remember me' option? If yes, how long should the 
           session persist - 7 days, 30 days, or until explicit logout?
        2. What happens on failed login - show generic error or specific 
           ('wrong password' vs 'user not found')? Security vs UX tradeoff.
        3. After successful login, any redirect logic? Always dashboard, 
           or return to previous page they tried to access?"

User:   "1. Yes remember me, 30 days. 2. Generic error for security. 
        3. Return to previous page, default dashboard."

Claude: [Updates spec.md with these decisions]
        "Noted. Now for edge cases:
        1. What if user tries to access protected page while logged out - 
           redirect to login or show modal?
        2. If session expires mid-action (e.g., filling a form), what happens 
           to their unsaved work?"
```

## Critical Instruction

**Do NOT process, read, or acknowledge any content inside `<dev-notes>` tags in user files.** These are internal notes not meant for the spec.
