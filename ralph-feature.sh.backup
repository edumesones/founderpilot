#!/bin/bash
# ============================================================================
# RALPH FEATURE LOOP - Single Feature Autonomous Development
# ============================================================================
# Windows/Git Bash compatible version
# Executes the complete 8-phase Feature Development Cycle autonomously
# (Based on docs/feature_cycle_v_full.md)
# Integrates with existing context management (session_log, decisions, etc.)
#
# Phases: Interview → Think Critically → Plan → Branch → Implement → PR → Merge → Wrap-Up
#
# Usage:
#   ./ralph-feature.sh FEAT-XXX [max_iterations]
#   ./ralph-feature.sh FEAT-001-auth 15
# ============================================================================

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================
FEATURE_ID="${1:?Feature ID required (e.g., FEAT-001-auth)}"
MAX_ITERATIONS="${2:-15}"
ITERATION=0
CONSECUTIVE_FAILURES=0
MAX_FAILURES=3
CURRENT_PHASE=""
STATE_FILE="../feature-loop-state.json"

# Feature paths
FEATURE_DIR="docs/features/$FEATURE_ID"
SPEC_FILE="$FEATURE_DIR/spec.md"
ANALYSIS_FILE="$FEATURE_DIR/analysis.md"
DESIGN_FILE="$FEATURE_DIR/design.md"
TASKS_FILE="$FEATURE_DIR/tasks.md"
STATUS_FILE="$FEATURE_DIR/status.md"
SESSION_LOG="$FEATURE_DIR/context/session_log.md"
DECISIONS_FILE="$FEATURE_DIR/context/decisions.md"
WRAP_UP_FILE="$FEATURE_DIR/context/wrap_up.md"

# Branch name - matches worktree branch format: feat/FEAT-XXX
BRANCH_NAME="feat/$(echo "$FEATURE_ID" | grep -oE 'FEAT-[0-9]+')"

# Claude CLI flags for non-interactive mode (Windows/Git Bash compatible)
CLAUDE_FLAGS="--dangerously-skip-permissions --output-format text"

# Colors disabled for Windows compatibility
RED=''
GREEN=''
YELLOW=''
BLUE=''
CYAN=''
NC=''

# ============================================================================
# LOGGING (Windows compatible - no colors, simple echo)
# ============================================================================
log_info() {
    echo "[$FEATURE_ID] $(date '+%H:%M:%S') - $1"
}

log_success() {
    echo "[$FEATURE_ID] $(date '+%H:%M:%S') [OK] $1"
}

log_warning() {
    echo "[$FEATURE_ID] $(date '+%H:%M:%S') [WARN] $1"
}

log_error() {
    echo "[$FEATURE_ID] $(date '+%H:%M:%S') [ERROR] $1"
}

log_phase() {
    echo ""
    echo "================================================================"
    echo "  $FEATURE_ID - Phase: $1"
    echo "  Iteration: $ITERATION / $MAX_ITERATIONS"
    echo "================================================================"
    echo ""
}

add_session_log() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M')
    
    if [[ -f "$SESSION_LOG" ]]; then
        # Prepend to log (after the header)
        local temp_file=$(mktemp)
        head -n 20 "$SESSION_LOG" > "$temp_file"
        echo "" >> "$temp_file"
        echo "### [$timestamp] - [RALPH] $message" >> "$temp_file"
        echo "" >> "$temp_file"
        tail -n +21 "$SESSION_LOG" >> "$temp_file" 2>/dev/null || true
        mv "$temp_file" "$SESSION_LOG"
    fi
}

# ============================================================================
# PHASE DETECTION
# ============================================================================
detect_current_phase() {
    # Check status.md for current phase
    if [[ ! -f "$STATUS_FILE" ]]; then
        echo "unknown"
        return
    fi

    # Check phase progress table (8-phase cycle from feature_cycle_v_full.md)
    local interview=$(grep -E "Interview.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local analysis=$(grep -E "Critical Analysis.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local plan=$(grep -E "Plan.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local branch=$(grep -E "Branch.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local implement=$(grep -E "Implement.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local pr=$(grep -E "PR.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local merge=$(grep -E "Merge.*✅" "$STATUS_FILE" 2>/dev/null || true)

    # Check wrap_up.md existence for final phase
    if [[ -f "$WRAP_UP_FILE" ]] && grep -q "Wrap-up completado\|Wrap-Up Complete" "$WRAP_UP_FILE" 2>/dev/null; then
        echo "complete"
    elif [[ -n "$merge" ]]; then
        echo "wrapup"
    elif [[ -n "$pr" ]]; then
        echo "merge"
    elif [[ -n "$implement" ]]; then
        echo "pr"
    elif [[ -n "$branch" ]]; then
        # Check if implementation is complete
        if is_implementation_complete; then
            echo "pr"
        else
            echo "implement"
        fi
    elif [[ -n "$plan" ]]; then
        echo "branch"
    elif [[ -n "$analysis" ]]; then
        echo "plan"
    elif [[ -n "$interview" ]]; then
        # Check if analysis is complete or should be skipped
        if is_analysis_complete; then
            echo "plan"
        else
            echo "analysis"
        fi
    else
        # Check if spec.md has decisions
        if is_interview_complete; then
            echo "analysis"
        else
            echo "interview"
        fi
    fi
}

is_interview_complete() {
    if [[ ! -f "$SPEC_FILE" ]]; then
        return 1
    fi
    
    # Check if Technical Decisions table has non-TBD values
    local decisions=$(grep -E "^\| [0-9]+ \|" "$SPEC_FILE" 2>/dev/null | grep -v "TBD" | wc -l)
    [[ $decisions -ge 2 ]]
}

is_plan_complete() {
    [[ -f "$DESIGN_FILE" ]] && [[ -f "$TASKS_FILE" ]] && \
        grep -q "## Backend Tasks\|## Tasks" "$TASKS_FILE" 2>/dev/null
}

is_branch_created() {
    git show-ref --verify --quiet "refs/heads/$BRANCH_NAME" 2>/dev/null
}

is_implementation_complete() {
    if [[ ! -f "$TASKS_FILE" ]]; then
        return 1
    fi
    
    local total=$(grep -cE "^- \[" "$TASKS_FILE" 2>/dev/null)
    local complete=$(grep -cE "^- \[x\]" "$TASKS_FILE" 2>/dev/null)
    total=${total:-0}
    complete=${complete:-0}
    total=$((total))
    complete=$((complete))

    # Consider complete if >90% done
    if [[ $total -gt 0 ]]; then
        local percent=$((complete * 100 / total))
        [[ $percent -ge 90 ]]
    else
        return 1
    fi
}

is_pr_created() {
    gh pr view --json state 2>/dev/null | grep -q '"state"' 2>/dev/null
}

is_pr_merged() {
    local state=$(gh pr view --json state 2>/dev/null | grep -oE '"state":"[^"]+"' | cut -d'"' -f4)
    [[ "$state" == "MERGED" ]]
}

is_analysis_complete() {
    # Check if analysis.md exists and has substantive content
    if [[ ! -f "$ANALYSIS_FILE" ]]; then
        return 1
    fi

    # Check for required sections (at least problem clarification and decision summary)
    local has_problem=$(grep -c "## 1\. Clarificación\|## Problem Clarification\|Step 1" "$ANALYSIS_FILE" 2>/dev/null)
    local has_decision=$(grep -c "## 11\. Resumen\|## Decision Summary\|Step 11\|Confidence Level" "$ANALYSIS_FILE" 2>/dev/null)

    # Default to 0 if empty, convert to integer (Git Bash compatibility)
    has_problem=${has_problem:-0}
    has_decision=${has_decision:-0}
    has_problem=$((has_problem))
    has_decision=$((has_decision))

    [[ $has_problem -ge 1 ]] && [[ $has_decision -ge 1 ]]
}

should_skip_analysis() {
    # Determine if analysis can be abbreviated or skipped based on feature complexity
    # Returns 0 (true) if can skip, 1 (false) if must analyze

    if [[ ! -f "$SPEC_FILE" ]]; then
        return 1  # Can't determine, must analyze
    fi

    # Check for bug fix / hotfix keywords
    local is_bugfix=$(grep -ciE "bug|fix|hotfix|patch" "$SPEC_FILE" 2>/dev/null)
    is_bugfix=${is_bugfix:-0}
    is_bugfix=$((is_bugfix))
    if [[ $is_bugfix -ge 2 ]]; then
        return 0  # Skip analysis for bug fixes
    fi

    return 1  # Default: must analyze
}

get_analysis_depth() {
    # Returns: full, medium, light, skip
    # Based on feature_cycle_v_full.md abbreviation rules

    if should_skip_analysis; then
        echo "skip"
        return
    fi

    # Check if this is a new system or existing patterns
    local has_patterns=$(find src -name "*.py" 2>/dev/null | head -5 | wc -l)
    has_patterns=${has_patterns:-0}
    has_patterns=$((has_patterns))

    if [[ $has_patterns -lt 5 ]]; then
        echo "full"  # New system, full 11 steps
    else
        # Existing system - check feature complexity
        local decision_count=$(grep -cE "^\| [0-9]+ \|" "$SPEC_FILE" 2>/dev/null)
        decision_count=${decision_count:-0}
        decision_count=$((decision_count))
        if [[ $decision_count -ge 5 ]]; then
            echo "medium"  # Complex feature, steps 1-2-3-5-9-11
        else
            echo "light"   # Simple feature, steps 1-2-5-11
        fi
    fi
}

# ============================================================================
# PHASE EXECUTION
# ============================================================================
execute_phase() {
    local phase="$1"
    CURRENT_PHASE="$phase"
    log_phase "$phase"
    
    case "$phase" in
        interview)
            execute_interview
            ;;
        analysis)
            execute_analysis
            ;;
        plan)
            execute_plan
            ;;
        branch)
            execute_branch
            ;;
        implement)
            execute_implement
            ;;
        pr)
            execute_pr
            ;;
        merge)
            execute_merge
            ;;
        wrapup)
            execute_wrapup
            ;;
        complete)
            log_success "Feature is already complete!"
            return 100  # Signal completion
            ;;
        *)
            log_error "Unknown phase: $phase"
            return 1
            ;;
    esac
}

execute_interview() {
    log_info "Executing Interview phase..."
    
    # Check if needs human input
    if ! is_interview_complete; then
        # Try to auto-complete if spec has enough structure
        local has_structure=$(grep -c "## Technical Decisions" "$SPEC_FILE" 2>/dev/null)
        has_structure=${has_structure:-0}
        has_structure=$((has_structure))

        if [[ $has_structure -eq 0 ]]; then
            log_warning "spec.md needs human input - Interview not complete"
            add_session_log "Interview needs human input - pausing"
            return 3  # Human input needed
        fi
    fi
    
    # Build prompt for Claude - write to temp file to avoid escaping issues
    local prompt_file=$(mktemp)
    cat > "$prompt_file" << EOF
You are executing the INTERVIEW phase for $FEATURE_ID.

Your job is to complete the spec.md file with ALL necessary information for this feature.

Context:
- Project overview: Read docs/features/_index.md to understand the project and this feature
- Project definition: Read docs/project.md if available
- This feature: $FEATURE_ID

Steps:
1. Read docs/features/_index.md to understand what this feature is about
2. Read $SPEC_FILE (currently a template)
3. Fill in ALL sections of the spec:
   - Summary: What this feature does (1-2 paragraphs)
   - User Stories: Real user stories for this feature
   - Acceptance Criteria: Clear definition of done
   - Technical Decisions: Replace ALL _TBD_ values with concrete decisions
   - Scope: What IS and is NOT included
   - Dependencies: What this feature needs/blocks
   - Edge Cases: How to handle errors
   - Security: Authentication, data sensitivity, etc.
4. Update $STATUS_FILE to mark Interview phase as ✅
5. Add checkpoint to $SESSION_LOG

Important:
- Fill EVERY section with REAL content, not placeholders
- Make technical decisions based on the project context
- If you genuinely cannot decide without human input, emit INTERVIEW_NEEDS_INPUT

When complete, emit: INTERVIEW_COMPLETE
If human input is needed, emit: INTERVIEW_NEEDS_INPUT
EOF

    # Run Claude with prompt from file (Windows/Git Bash compatible - no pipe)
    echo "DEBUG: Calling claude -p with prompt from file..."
    local prompt_content=$(cat "$prompt_file")
    rm -f "$prompt_file"

    echo "===== CLAUDE OUTPUT START ====="
    local output=$(claude -p "$prompt_content" $CLAUDE_FLAGS 2>&1)
    echo "$output"
    echo "===== CLAUDE OUTPUT END ====="
    echo ""
    echo "DEBUG: Claude returned, output length: ${#output} chars"

    # Check for completion signal
    if echo "$output" | grep -qi "INTERVIEW_COMPLETE"; then
        log_success "Interview phase complete"
        add_session_log "Interview Complete - Decisions documented"
        return 0
    elif echo "$output" | grep -qi "INTERVIEW_NEEDS_INPUT"; then
        log_warning "Interview needs human input"
        return 3
    else
        log_error "Interview phase failed - no completion signal found"
        echo "DEBUG: Full output was:"
        echo "$output"
        return 1
    fi
}

execute_analysis() {
    log_info "Executing Think Critically phase..."

    # Check if already complete
    if is_analysis_complete; then
        log_info "Analysis already complete, skipping..."
        return 0
    fi

    # Determine analysis depth
    local depth=$(get_analysis_depth)
    log_info "Analysis depth: $depth"

    if [[ "$depth" == "skip" ]]; then
        log_info "Skipping analysis (bug fix / hotfix detected)"
        # Create minimal analysis.md
        cat > "$ANALYSIS_FILE" << 'ANALYSIS_EOF'
# Critical Analysis - SKIPPED

**Reason:** Bug fix / hotfix - no architectural risk
**Depth:** Skip
**Confidence:** High

Proceeding directly to Plan phase.
ANALYSIS_EOF
        add_session_log "Analysis Skipped - Bug fix/hotfix"
        return 0
    fi

    # Build prompt based on depth
    local steps_to_run=""
    case "$depth" in
        full)
            steps_to_run="ALL 11 STEPS (1-2-3-4-5-6-7-8-9-10-11)"
            ;;
        medium)
            steps_to_run="Steps 1, 2, 3, 5, 9, 11 (medium complexity)"
            ;;
        light)
            steps_to_run="Steps 1, 2, 5, 11 (light complexity)"
            ;;
    esac

    # Simplified prompt for faster execution
    local prompt="THINK CRITICALLY for $FEATURE_ID (depth: $depth). Read $SPEC_FILE, create $ANALYSIS_FILE with: 1)Problem 2)Assumptions 5)Failures 11)Decision+Confidence. Update $STATUS_FILE. Emit ANALYSIS_COMPLETE when done, or ANALYSIS_NEEDS_REVIEW if red flags."

    # Run Claude with simplified prompt
    log_info "Running analysis protocol (depth: $depth)..."
    echo "===== CLAUDE OUTPUT START ====="
    local output=$(claude -p "$prompt" $CLAUDE_FLAGS 2>&1)
    echo "$output"
    echo "===== CLAUDE OUTPUT END ====="
    echo ""

    # Check for signals
    if echo "$output" | grep -qi "ANALYSIS_COMPLETE"; then
        log_success "Think Critically phase complete"
        add_session_log "Critical Analysis Complete - Confidence verified"
        return 0
    elif echo "$output" | grep -qi "ANALYSIS_NEEDS_REVIEW"; then
        log_warning "Analysis requires human review (pause condition triggered)"
        add_session_log "[PAUSED] Critical Analysis needs review - see analysis.md"
        return 3  # Human input needed
    else
        log_error "Think Critically phase failed"
        return 1
    fi
}

execute_plan() {
    log_info "Executing Plan phase..."

    if is_plan_complete; then
        log_info "Plan already complete, skipping..."
        return 0
    fi
    
    local prompt=$(cat << EOF
You are executing the PLAN phase (Phase 3) for $FEATURE_ID.

Create the technical design and task breakdown, informed by the critical analysis.

Steps:
1. Read BOTH inputs (MANDATORY):
   - $SPEC_FILE for requirements and decisions
   - $ANALYSIS_FILE for architectural guidance and risk mitigations
2. Generate $DESIGN_FILE with:
   - Architecture overview (use recommended approach from analysis)
   - Data models
   - API design
   - File structure
   - Error handling (from failure analysis)
   - Observability tasks (from analysis Step 7)
3. Generate $TASKS_FILE with ordered task checklist including:
   - Implementation tasks
   - Mitigation tasks from analysis
   - Monitoring/observability tasks
4. Update status.md to mark Plan as ✅
5. Add checkpoint to context/session_log.md

Follow the templates in docs/features/_template/

When complete, emit: <phase>PLAN_COMPLETE</phase>
EOF
)
    
    echo "===== CLAUDE OUTPUT START ====="
    local output=$(claude -p "$prompt" $CLAUDE_FLAGS 2>&1)
    echo "$output"
    echo "===== CLAUDE OUTPUT END ====="
    echo ""
    
    if echo "$output" | grep -q "<phase>PLAN_COMPLETE</phase>"; then
        log_success "Plan phase complete"
        add_session_log "Plan Complete ✅ - Design and tasks created"
        return 0
    else
        log_error "Plan phase failed"
        return 1
    fi
}

execute_branch() {
    log_info "Executing Branch phase..."
    
    if is_branch_created; then
        log_info "Branch already exists: $BRANCH_NAME"
        # Just checkout
        git checkout "$BRANCH_NAME" 2>/dev/null || true
        return 0
    fi
    
    # Create branch
    git checkout main 2>/dev/null || git checkout master
    git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || true
    git checkout -b "$BRANCH_NAME"
    
    log_success "Branch created: $BRANCH_NAME"
    add_session_log "Branch Created ✅ - $BRANCH_NAME"
    
    # Update status
    local prompt=$(cat << EOF
Update $STATUS_FILE to mark Branch phase as ✅.
Add the branch name: $BRANCH_NAME

Emit: <phase>BRANCH_COMPLETE</phase>
EOF
)
    
    echo "===== CLAUDE OUTPUT START ====="
    claude -p "$prompt" $CLAUDE_FLAGS 2>&1 || true
    echo "===== CLAUDE OUTPUT END ====="
    echo ""
    return 0
}

execute_implement() {
    log_info "Executing Implement phase..."
    
    # Count tasks
    local total=$(grep -cE "^- \[" "$TASKS_FILE" 2>/dev/null)
    local complete=$(grep -cE "^- \[x\]" "$TASKS_FILE" 2>/dev/null)
    total=${total:-0}
    complete=${complete:-0}
    total=$((total))
    complete=$((complete))
    local remaining=$((total - complete))
    
    log_info "Tasks: $complete/$total complete ($remaining remaining)"
    
    if [[ $remaining -eq 0 ]]; then
        log_success "All tasks complete!"
        add_session_log "Implementation Complete ✅ - All $total tasks done"
        return 0
    fi
    
    # Process up to 3 tasks per iteration
    local batch_size=3
    
    local prompt=$(cat << EOF
You are executing the IMPLEMENT phase for $FEATURE_ID.
This is iteration $ITERATION.

Current progress: $complete/$total tasks complete.

Steps:
1. Read $TASKS_FILE to find next uncompleted tasks (marked with [ ])
2. Complete up to $batch_size tasks:
   - Mark task as [🟡] before starting
   - Implement the code
   - Mark task as [x] when done
   - Commit: git add . && git commit -m "$FEATURE_ID: [task description]"
3. Update progress in status.md
4. Add log entry to context/session_log.md

If all tasks are complete, emit: <phase>IMPLEMENT_COMPLETE</phase>
If some tasks done but more remain, emit: <phase>IMPLEMENT_PROGRESS</phase>
EOF
)
    
    echo "===== CLAUDE OUTPUT START ====="
    local output=$(claude -p "$prompt" $CLAUDE_FLAGS 2>&1)
    echo "$output"
    echo "===== CLAUDE OUTPUT END ====="
    echo ""
    
    if echo "$output" | grep -q "<phase>IMPLEMENT_COMPLETE</phase>"; then
        log_success "Implementation complete"
        return 0
    elif echo "$output" | grep -q "<phase>IMPLEMENT_PROGRESS</phase>"; then
        log_info "Progress made, continuing..."
        add_session_log "Implementation Progress - Batch complete"
        return 0
    else
        log_warning "No progress signal detected"
        return 1
    fi
}

execute_pr() {
    log_info "Executing PR phase..."
    
    if is_pr_created; then
        log_info "PR already exists"
        return 0
    fi
    
    # Push branch
    git push -u origin "$BRANCH_NAME" 2>/dev/null || true
    
    # Create PR
    local pr_title="$FEATURE_ID: $(echo "$FEATURE_ID" | sed 's/FEAT-[0-9]*-//' | tr '-' ' ' | sed 's/.*/\u&/')"
    
    gh pr create \
        --title "$pr_title" \
        --body "## Summary

Automated PR for $FEATURE_ID

## Checklist
- [x] Implementation complete
- [x] Tests passing
- [ ] Review approved

---
*Created by Ralph Loop*" \
        --base main 2>/dev/null || true
    
    log_success "PR created"
    add_session_log "PR Created ✅"
    
    # Update status
    local prompt=$(cat << EOF
Update $STATUS_FILE to mark PR phase as ✅.
Add PR link if available.

Emit: <phase>PR_COMPLETE</phase>
EOF
)
    
    echo "===== CLAUDE OUTPUT START ====="
    claude -p "$prompt" $CLAUDE_FLAGS 2>&1 || true
    echo "===== CLAUDE OUTPUT END ====="
    echo ""
    return 0
}

execute_merge() {
    log_info "Checking merge status..."
    
    if is_pr_merged; then
        log_success "PR is merged!"
        add_session_log "Merged ✅ - PR merged to main"
        return 0
    fi
    
    # Check PR status
    local state=$(gh pr view --json state 2>/dev/null | grep -oE '"state":"[^"]+"' | cut -d'"' -f4 || echo "unknown")
    
    if [[ "$state" == "OPEN" ]]; then
        log_warning "PR is open, waiting for approval..."
        return 2  # Waiting
    elif [[ "$state" == "CLOSED" ]]; then
        log_error "PR was closed without merging"
        return 1
    fi
    
    log_info "Merge status: $state"
    return 2
}

execute_wrapup() {
    log_info "Executing Wrap-up phase..."
    
    if [[ -f "$WRAP_UP_FILE" ]] && grep -q "Wrap-up completado" "$WRAP_UP_FILE" 2>/dev/null; then
        log_success "Wrap-up already complete"
        return 100
    fi
    
    local prompt=$(cat << EOF
You are executing the WRAP-UP phase for $FEATURE_ID.

This is the final phase. Complete the wrap-up documentation.

Steps:
1. Create/update $WRAP_UP_FILE using the template in docs/features/_template/context/wrap-up.md
2. Fill in:
   - Metadata (dates, times, PR number)
   - Summary of what was accomplished
   - Metrics from tasks.md
   - Key decisions from context/decisions.md
   - Learnings
3. Update status.md to mark complete with Wrap-up ✅
4. Add final entry to session_log.md

When complete, emit: <phase>WRAPUP_COMPLETE</phase>
Then emit: <phase>FEATURE_COMPLETE</phase>
EOF
)
    
    echo "===== CLAUDE OUTPUT START ====="
    local output=$(claude -p "$prompt" $CLAUDE_FLAGS 2>&1)
    echo "$output"
    echo "===== CLAUDE OUTPUT END ====="
    echo ""
    
    if echo "$output" | grep -q "<phase>FEATURE_COMPLETE</phase>"; then
        log_success "Feature complete! [COMPLETE]"
        add_session_log "Feature Complete [COMPLETE] - Wrap-up done"
        return 100
    elif echo "$output" | grep -q "<phase>WRAPUP_COMPLETE</phase>"; then
        log_success "Wrap-up complete"
        return 100
    else
        log_error "Wrap-up failed"
        return 1
    fi
}

# ============================================================================
# UPDATE STATE FILE
# ============================================================================
update_state() {
    local status="$1"
    local phase="$2"
    
    if [[ -f "$STATE_FILE" ]]; then
        python << EOF
import json
from datetime import datetime
with open('$STATE_FILE', 'r') as f:
    state = json.load(f)
if '$FEATURE_ID' in state['features']:
    state['features']['$FEATURE_ID']['status'] = '$status'
    state['features']['$FEATURE_ID']['phase'] = '$phase'
    state['features']['$FEATURE_ID']['iterations'] = $ITERATION
    state['features']['$FEATURE_ID']['failures'] = $CONSECUTIVE_FAILURES
    state['features']['$FEATURE_ID']['updated_at'] = datetime.now().isoformat()
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
EOF
    fi
}

# ============================================================================
# MAIN LOOP
# ============================================================================
main() {
    echo "DEBUG: Entering main()"
    echo "DEBUG: FEATURE_ID=$FEATURE_ID"
    echo "DEBUG: FEATURE_DIR=$FEATURE_DIR"
    log_info "Starting Ralph Feature Loop for $FEATURE_ID"
    log_info "Max iterations: $MAX_ITERATIONS"

    echo "DEBUG: Checking feature dir..."
    # Verify feature exists
    if [[ ! -d "$FEATURE_DIR" ]]; then
        log_error "Feature directory not found: $FEATURE_DIR"
        exit 1
    fi
    echo "DEBUG: Feature dir exists"

    echo "DEBUG: Checking branch..."
    # Ensure on correct branch if it exists
    if is_branch_created; then
        echo "DEBUG: Branch exists, checking out..."
        git checkout "$BRANCH_NAME" 2>/dev/null || true
    fi
    echo "DEBUG: Branch check done"

    echo "DEBUG: Entering loop..."
    while [[ $ITERATION -lt $MAX_ITERATIONS ]]; do
        ITERATION=$((ITERATION + 1))
        echo "DEBUG: Iteration $ITERATION"

        # Detect current phase
        echo "DEBUG: Detecting phase..."
        local phase=$(detect_current_phase)
        echo "DEBUG: Phase detected: $phase"
        log_info "Detected phase: $phase"
        
        # Update state
        update_state "running" "$phase"
        
        # Execute phase
        execute_phase "$phase"
        local result=$?
        
        case $result in
            0)
                # Success - reset failure counter
                CONSECUTIVE_FAILURES=0
                log_success "Phase $phase completed successfully"
                ;;
            1)
                # Failure
                CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
                log_error "Phase $phase failed (failure $CONSECUTIVE_FAILURES/$MAX_FAILURES)"
                
                if [[ $CONSECUTIVE_FAILURES -ge $MAX_FAILURES ]]; then
                    log_error "Too many consecutive failures. Pausing for human intervention."
                    update_state "paused" "$phase"
                    add_session_log "[WARN] Paused after $CONSECUTIVE_FAILURES failures in $phase phase"
                    exit 1
                fi
                ;;
            2)
                # Waiting (e.g., for merge approval)
                log_info "Waiting for external action (merge approval)..."
                update_state "waiting" "$phase"
                sleep 60  # Wait 1 minute before checking again
                ;;
            3)
                # Human input needed
                log_warning "Human input required. Pausing loop."
                update_state "needs_input" "$phase"
                add_session_log "[PAUSED] Paused - Human input needed in $phase phase"
                exit 0
                ;;
            100)
                # Feature complete
                log_success "[COMPLETE] Feature $FEATURE_ID is complete!"
                update_state "complete" "done"
                exit 0
                ;;
        esac
        
        # Small delay between iterations
        sleep 2
    done
    
    log_warning "Max iterations ($MAX_ITERATIONS) reached"
    update_state "max_iterations" "$CURRENT_PHASE"
    add_session_log "[WARN] Max iterations reached at $CURRENT_PHASE phase"
    exit 0
}

# ============================================================================
# RUN
# ============================================================================
main
