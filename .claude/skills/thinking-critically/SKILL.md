---
name: thinking-critically
description: Deep engineering analysis before implementation (Phase 2 of 8-Phase Feature Cycle). Challenges assumptions, identifies unknowns, and prevents architectural mistakes. Use when planning complex features, writing PRDs, designing systems, or before any significant code changes. Triggers on "think critically about", "analyze this approach", "challenge my assumptions", "review this design", "what could go wrong", "help me think through", or when user mentions PRD, architecture decisions, or system design.
globs: ["docs/features/**/spec.md", "docs/features/**/analysis.md", "docs/architecture/**"]
---

# Thinking Critically

Rigorous pre-implementation analysis that simulates a paranoid staff engineer review. This skill prevents costly architectural mistakes by forcing systematic examination of assumptions, trade-offs, and failure modes **before** writing code.

**Phase 2 of the 8-Phase Feature Development Cycle:**
```
Interview → THINK CRITICALLY → Plan → Branch → Implement → PR → Merge → Wrap-Up
             ↑ YOU ARE HERE
```

## Philosophy

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  "The best time to find a design flaw is before you write the code."         ║
║  "Every assumption you don't question is a bug waiting to happen."           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

## When to Use

- Planning a new feature or system (Phase 2 of Feature Cycle)
- Writing or reviewing a PRD
- Making architectural decisions
- Before implementing anything complex
- When something "feels off" but you can't articulate why
- After getting initial requirements, before diving into code

## Prerequisites

- Feature spec completed (Phase 1: Interview ✅)
- `docs/features/FEAT-XXX/spec.md` exists with decisions
- `docs/project.md` exists (for project context)
- `docs/architecture/_index.md` exists (for technical constraints)

## Process

### 0. Read Context First

```bash
# Read feature spec (REQUIRED - output of Interview phase)
cat docs/features/FEAT-XXX/spec.md

# Read project context
cat docs/project.md 2>/dev/null

# Read architecture constraints
cat docs/architecture/_index.md 2>/dev/null

# Check Market Validation (from SaaS Validator integration)
grep -A5 "Pain Level\|Market Validation\|painkiller" docs/features/FEAT-XXX/spec.md 2>/dev/null

# Check current status
cat docs/features/FEAT-XXX/status.md
```

### 0.1 Determine Analysis Depth

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  AUTOMATIC ABBREVIATION RULES                                                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Condition                        │ Steps Executed     │ Reason               ║
║  ─────────────────────────────────┼────────────────────┼──────────────────── ║
║  New feature + new system         │ All 11 steps       │ Max architectural    ║
║                                   │                    │ risk                 ║
║  New feature + existing patterns  │ 1-2-3-5-9-11      │ Medium risk          ║
║  Small/clear scope feature        │ 1-2-5-11          │ Low risk             ║
║  Bug fix / hotfix                 │ SKIP entirely      │ No architectural     ║
║                                   │                    │ risk                 ║
║                                                                               ║
║  When in doubt → execute ALL 11 steps                                        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## The 11-Step Critical Analysis Protocol

Execute ALL steps in order. Do not skip steps unless explicitly told to or abbreviation rules apply.

### Step 1: Problem Clarification & Constraints

**Goal:** Define exactly what we're solving and within what boundaries.

**Questions to answer:**
- What is the core problem statement in one sentence?
- What are the hard constraints? (budget, time, team size, existing systems)
- What are the soft constraints? (preferences, nice-to-haves)
- What does success look like? How will we measure it?
- What is explicitly NOT a goal?

**Output format:**
```markdown
## 1. Problem Clarification

### Problem Statement
[One clear sentence]

### Hard Constraints
- [Constraint 1]
- [Constraint 2]

### Soft Constraints
- [Preference 1]

### Success Criteria
- [Measurable criterion 1]
- [Measurable criterion 2]

### Non-Goals
- [What we're NOT trying to solve]
```

---

### Step 2: Implicit Assumptions Identification

**Goal:** Surface hidden assumptions that could invalidate the entire approach.

**⚠️ THIS IS THE MOST CRITICAL STEP.** Most architectural failures stem from unstated assumptions.

**Categories to examine:**

| Category | Example Assumptions |
|----------|---------------------|
| Users | "Users have stable internet", "Users understand X" |
| Data | "Data fits in memory", "IDs are unique" |
| Scale | "We'll never exceed X requests/sec" |
| Environment | "Always runs on Linux", "Has access to GPU" |
| Dependencies | "API will always be available", "Response time < 100ms" |
| Security | "Internal network is trusted", "Users don't lie" |
| Business | "Requirements won't change", "Budget is fixed" |
| Market | "Users will pay for this", "Pain level is real" |

**Output format:**
```markdown
## 2. Implicit Assumptions

| # | Assumption | If Wrong, Impact | Confidence | Category |
|---|------------|------------------|------------|----------|
| 1 | [Assumption] | [What breaks] | High/Med/Low | [Cat] |
| 2 | [Assumption] | [What breaks] | High/Med/Low | [Cat] |

### ⚠️ Assumptions Requiring Validation
- [ ] [Low confidence + High impact assumption]
- [ ] [Low confidence + High impact assumption]
```

**CRITICAL RULE:** If any assumption has **Low confidence** AND **High impact** → **STOP**. In Ralph Loop, emit `<phase>ANALYSIS_PAUSE</phase>`. In manual mode, ask user to validate before proceeding.

---

### Step 3: Design Space Exploration

**Goal:** Enumerate possible approaches before committing to one.

**Explore at minimum 3 different approaches:**
1. The obvious/default approach
2. The "simpler than you think" approach
3. The "what if we're wrong about constraints" approach

**For each approach, document:**
- Core idea in 1-2 sentences
- Key technical choices
- Main advantages
- Main disadvantages
- When this approach shines

**Output format:**
```markdown
## 3. Design Space Exploration

### Approach A: [Name]
**Core idea:** [Description]
**Pros:** [List]
**Cons:** [List]
**Best when:** [Conditions]
**Effort:** [Low/Med/High]

### Approach B: [Name]
...

### Approach C: [Name]
...

### Preliminary Recommendation
[Which approach and why, pending trade-off analysis]
```

---

### Step 4: Trade-off Analysis

**Goal:** Explicitly weigh competing concerns.

**Common trade-off dimensions:**

| Dimension A | vs | Dimension B |
|-------------|-----|-------------|
| Speed | ↔ | Reliability |
| Simplicity | ↔ | Flexibility |
| Cost | ↔ | Performance |
| Security | ↔ | Usability |
| Consistency | ↔ | Availability |
| Build | ↔ | Buy |
| Now | ↔ | Later |

**For this specific problem, identify:**
1. Which trade-offs are relevant?
2. Where on the spectrum should we land?
3. Why that position?

**Output format:**
```markdown
## 4. Trade-off Analysis

### [Trade-off 1]: [A] vs [B]
**Position:** Favor [A/B] because [reason]
**Implications:** [What this means for implementation]

### [Trade-off 2]: [A] vs [B]
...
```

---

### Step 5: Failure-First Analysis

**Goal:** Systematically identify what can go wrong.

**Categories of failures to consider:**
- **Technical:** Crashes, data loss, performance degradation
- **Operational:** Deployment failures, monitoring gaps, scaling issues
- **Integration:** API changes, dependency failures, version conflicts
- **Human:** Misuse, confusion, training gaps
- **Business:** Requirement changes, budget cuts, timeline shifts

**Output format:**
```markdown
## 5. Failure-First Analysis

### Critical Failures (High Severity)

| Failure Mode | Probability | Severity | Detection | Mitigation |
|--------------|-------------|----------|-----------|------------|
| [What fails] | H/M/L | H/M/L | [How we'd know] | [Prevention] |

### Likely Failures (High Probability)

| Failure Mode | Probability | Severity | Detection | Mitigation |
|--------------|-------------|----------|-----------|------------|
| [What fails] | H/M/L | H/M/L | [How we'd know] | [Prevention] |

### Cascading Failures
- If [A] fails → [B] breaks → [C] is impacted
```

---

### Step 6: Boundaries & Invariants

**Goal:** Define what must ALWAYS be true and what the system will NEVER do.

**Invariants:** Conditions that must hold at all times
- Data invariants: "User balance >= 0"
- State invariants: "Connection always authenticated before data transfer"
- Ordering invariants: "Event A always before Event B"

**Boundaries:** Hard limits the system respects

**Output format:**
```markdown
## 6. Boundaries & Invariants

### Invariants (Must ALWAYS be true)
1. [Invariant 1]
2. [Invariant 2]

### Boundaries (Hard limits)

| Boundary | Limit | Enforcement |
|----------|-------|-------------|
| [What] | [Value] | [How enforced] |

### What the System Will NEVER Do
- [Anti-behavior 1]
- [Anti-behavior 2]
```

---

### Step 7: Observability & Control

**Goal:** Ensure the system can be monitored and managed.

**Questions to answer:**
- How will we know if it's working correctly?
- How will we know if it's failing?
- What metrics matter?
- What logs are essential?
- How do we debug production issues?
- What manual interventions might be needed?

**Output format:**
```markdown
## 7. Observability & Control

### Key Metrics

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| [Metric] | [Why it matters] | [When to alert] |

### Essential Logs
- [Log 1]: [What it captures]

### Debug Capabilities
- [How to investigate issue X]

### Manual Controls
- [What operators can do to intervene]
```

---

### Step 8: Reversibility & Entropy

**Goal:** Assess how hard it is to undo decisions and recover from mistakes.

**Output format:**
```markdown
## 8. Reversibility & Entropy

### Decision Reversibility

| Decision | Reversibility | Cost to Reverse | Time to Reverse |
|----------|---------------|-----------------|-----------------|
| [Decision] | Easy/Hard/Impossible | [Effort] | [Duration] |

### Easy to Reverse
- [Decision]: [How to reverse]

### Hard to Reverse
- [Decision]: [Why difficult, what's needed]

### Irreversible
- [Decision]: [Why locked in, mitigations]

### Entropy Analysis
- **State accumulation:** [What grows over time]
- **Complexity growth:** [How system gets harder to maintain]
- **Migration path:** [How to evolve/replace later]
```

---

### Step 9: Adversarial Review (Paranoid Staff Engineer Mode)

**Goal:** Attack the design from every angle.

Adopt the persona of a paranoid, experienced staff engineer who has seen projects fail in every possible way. Challenge everything.

**Questions to ask:**
1. "Are we over-engineering this? What's the simplest thing that could work?"
2. "Are we under-engineering this? What obvious thing are we ignoring?"
3. "What's the 2 AM production incident this design will cause?"
4. "What will the new engineer who inherits this curse us for?"
5. "What happens when this is 10x the scale?"
6. "What happens when requirements change (and they will)?"
7. "What's the security hole we're not seeing?"
8. "What's the edge case that will corrupt data?"

**Output format:**
```markdown
## 9. Adversarial Review

### Over-engineering Concerns
- [Concern]: [Simpler alternative]

### Under-engineering Concerns
- [Concern]: [What we're missing]

### The 2AM Incident
- [Most likely production emergency]: [How it happens]

### Future Pain Points
- [What will hurt later]: [Why]

### Security Concerns
- [Potential vulnerability]: [Attack vector]

### Scale Concerns
- [What breaks at scale]: [How it breaks]

### 🚩 Red Flags Found
- [Critical red flag if any]
```

**CRITICAL RULE:** If a critical red flag is found → in Ralph Loop, emit `<phase>ANALYSIS_PAUSE</phase>`. In manual mode, warn user explicitly.

---

### Step 10: AI Delegation Assessment

**Goal:** Determine what AI (Ralph Loop) can safely handle vs what needs human oversight.

**Output format:**
```markdown
## 10. AI Delegation Matrix

### Safe for Full AI Automation (Ralph Loop)
- [Task]: [Why safe]

### AI with Human Review
- [Task]: [What to review]

### Human Only
- [Task]: [Why AI should not do this]
```

**Safe for AI:**
- Well-defined, deterministic tasks
- Low-risk operations with easy rollback
- Pattern-matching on known structures

**Requires Human Oversight:**
- Irreversible operations
- Security-sensitive decisions
- Ambiguous requirements
- Business-critical changes

---

### Step 11: Decision Summary

**Goal:** Synthesize everything into actionable conclusions.

**Output format:**
```markdown
## 11. Decision Summary

### Recommended Approach
[Selected approach and why - references Step 3]

### Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| [Decision] | [Choice] | [Why] |

### Short-term Goals (This Implementation)
1. [Goal 1]
2. [Goal 2]

### Long-term Considerations
- [Future consideration 1]
- [Future consideration 2]

### Remaining Unknowns
- [ ] [Unknown 1]: [How to resolve]
- [ ] [Unknown 2]: [How to resolve]

### Security Threat Model

| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| [Threat] | [L] | [I] | [M] |

### Blast Radius Analysis
- If [component] fails: [Impact scope]
- Maximum blast radius: [Worst case impact]

### Confidence Level
**[High/Medium/Low]** - [Why this confidence level]

### Red Flags to Watch
- [Warning sign 1]
- [Warning sign 2]

### Recommended Next Steps
1. [Immediate action - usually "Proceed to Plan phase"]
2. [Follow-up action]
```

**CRITICAL RULE:** If Confidence Level is **"Low"** → in Ralph Loop, emit `<phase>ANALYSIS_PAUSE</phase>`. Cannot proceed to Plan without human validation.

---

## Quick Reference: The 11 Steps

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     THINKING CRITICALLY - 11 STEPS                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. PROBLEM CLARIFICATION     - What exactly are we solving?              │
│   2. ASSUMPTIONS ⚠️ CRITICAL   - What are we assuming is true?             │
│   3. DESIGN SPACE              - What approaches exist?                    │
│   4. TRADE-OFFS                - What are we trading for what?             │
│   5. FAILURE-FIRST             - What will break and how?                  │
│   6. BOUNDARIES                - What must always/never be true?           │
│   7. OBSERVABILITY             - How will we know it works?                │
│   8. REVERSIBILITY             - Can we undo this?                         │
│   9. ADVERSARIAL 🔴            - Attack your own design                    │
│  10. AI DELEGATION             - What's safe to automate?                  │
│  11. DECISION SUMMARY          - Final synthesis + confidence level        │
│                                                                             │
│  Abbreviated (low risk): Steps 1 → 2 → 5 → 11                             │
│  Medium risk:            Steps 1 → 2 → 3 → 5 → 9 → 11                    │
│  Full (high risk):       ALL 11 steps                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Ralph Loop Integration

### As Iteration 2 in Autonomous Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Ralph Loop Iteration 2: THINK CRITICALLY                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUT:                                                                      │
│  ├── docs/features/FEAT-XXX/spec.md       (from Interview)                  │
│  ├── docs/project.md                       (project context)                │
│  ├── docs/architecture/_index.md           (tech constraints)               │
│  └── Market Validation data                (from SaaS Validator)            │
│                                                                              │
│  PROCESS:                                                                    │
│  ├── Determine analysis depth (abbreviation rules)                          │
│  ├── Execute 11-step protocol (or abbreviated)                              │
│  └── Generate analysis.md                                                    │
│                                                                              │
│  OUTPUT:                                                                     │
│  ├── docs/features/FEAT-XXX/analysis.md    (analysis results)               │
│  ├── docs/features/FEAT-XXX/status.md      (Phase: Critical Analysis ✅)    │
│  └── docs/features/FEAT-XXX/context/decisions.md  (enriched)                │
│                                                                              │
│  PAUSE CONDITIONS (any one triggers pause):                                  │
│  ├── 🔴 Step 2: Low confidence + High impact assumption                     │
│  ├── 🔴 Step 9: Critical red flag identified                                │
│  └── 🔴 Step 11: Confidence level = "Low"                                   │
│                                                                              │
│  If all checks pass → emit ANALYSIS_COMPLETE → continue to Plan             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### How Analysis Feeds Plan Phase

Plan phase (Iteration 3) reads `analysis.md` **in addition to** `spec.md` to:

| Analysis Output | How Plan Uses It |
|----------------|-----------------|
| Recommended approach (Step 11) | Selects architecture pattern for design.md |
| Failure mitigations (Step 5) | Adds error handling tasks to tasks.md |
| Invariants/boundaries (Step 6) | Becomes validation rules in implementation |
| AI delegation matrix (Step 10) | Decides Ralph automation scope per task |
| Observability requirements (Step 7) | Adds monitoring tasks to tasks.md |
| Trade-off positions (Step 4) | Guides technical choices in design.md |

---

## Output: analysis.md

After completing the protocol, save output to `docs/features/FEAT-XXX/analysis.md` using the analysis template.

## Status Updates

After completing analysis:

1. **Update status.md:**
   ```
   | Critical Analysis | ✅ Complete | {date} | [Full/Abbreviated] |
   ```

2. **Update _index.md:**
   ```
   | FEAT-XXX | [Name] | 🟡 In Progress | Critical Analysis ✅ |
   ```

3. **Update context/decisions.md** with key decisions from Step 11

4. **Append to status-log.md:**
   ```
   ### {timestamp}
   - **Action:** Critical Analysis complete
   - **Feature:** FEAT-XXX
   - **Depth:** Full (11 steps) / Abbreviated (4 steps)
   - **Confidence:** High/Medium/Low
   - **Red flags:** [count]
   ```

## Completion Message

```
✅ Critical Analysis complete for FEAT-XXX

Generated:
- docs/features/FEAT-XXX/analysis.md ([Full/Abbreviated] - [N] steps)

Confidence: [High/Medium/Low]
Red flags: [count]
Assumptions requiring validation: [count]

Updated:
- status.md → Phase: Critical Analysis ✅
- _index.md → Phase progress updated
- context/decisions.md → Key decisions added

Next step:
- "/plan implement FEAT-XXX" → Creates technical design using spec.md + analysis.md
```

---

## When to Skip or Abbreviate

**Skip entirely:**
- Bug fixes with obvious causes
- Typo corrections
- Documentation updates

**Abbreviated (Steps 1-2-5-11 only):**
- Small features with clear scope
- Following established patterns exactly
- Time-critical hotfixes (but review after)

**Full protocol (all 11 steps):**
- New systems or services
- Significant architectural changes
- Anything touching security, payments, or data integrity
- When "something feels off"
- First feature in a new project

---

## Integration with Other Skills

| Skill | Integration |
|-------|------------|
| `spec-architect` | Think Critically validates spec output |
| `implementation-planner` | Reads analysis.md to inform design.md |
| `saas-validator` | Market validation feeds into Step 2 assumptions |
| `ralph-loop` | Think Critically is autonomous Iteration 2 with conditional pause |
| `architecture-designer` | Run Think Critically for each major ADR |
| `status-reporter` | Updates all status files after completion |
