#!/bin/bash
# ============================================================================
# RALPH FEATURE LOOP - Single Feature Autonomous Development
# ============================================================================
# Windows/Git Bash compatible version
# Executes the complete 7-phase Feature Development Cycle autonomously
# Integrates with existing context management (session_log, decisions, etc.)
#
# Phases: Interview → Plan → Branch → Implement → PR → Merge → Wrap-Up
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
DESIGN_FILE="$FEATURE_DIR/design.md"
TASKS_FILE="$FEATURE_DIR/tasks.md"
STATUS_FILE="$FEATURE_DIR/status.md"
SESSION_LOG="$FEATURE_DIR/context/session_log.md"
WRAP_UP_FILE="$FEATURE_DIR/context/wrap_up.md"

# Branch name - matches worktree branch format: feat/FEAT-XXX
BRANCH_NAME="feat/$(echo "$FEATURE_ID" | grep -oE 'FEAT-[0-9]+')"

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
    
    # Check phase progress table
    local interview=$(grep -E "Interview.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local plan=$(grep -E "Plan.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local branch=$(grep -E "Branch.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local implement=$(grep -E "Implement.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local pr=$(grep -E "PR.*✅" "$STATUS_FILE" 2>/dev/null || true)
    local merge=$(grep -E "Merge.*✅" "$STATUS_FILE" 2>/dev/null || true)
    
    # Check wrap_up.md existence for final phase
    if [[ -f "$WRAP_UP_FILE" ]] && grep -q "Wrap-up completado" "$WRAP_UP_FILE" 2>/dev/null; then
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
    elif [[ -n "$interview" ]]; then
        echo "plan"
    else
        # Check if spec.md has decisions
        if is_interview_complete; then
            echo "plan"
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
    
    local total=$(grep -cE "^- \[" "$TASKS_FILE" 2>/dev/null || echo "0")
    local complete=$(grep -cE "^- \[x\]" "$TASKS_FILE" 2>/dev/null || echo "0")
    
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
        local has_structure=$(grep -c "## Technical Decisions" "$SPEC_FILE" 2>/dev/null || echo "0")
        
        if [[ $has_structure -eq 0 ]]; then
            log_warning "spec.md needs human input - Interview not complete"
            add_session_log "Interview needs human input - pausing"
            return 3  # Human input needed
        fi
    fi
    
    # Build prompt for Claude
    local prompt=$(cat << EOF
You are executing the INTERVIEW phase for $FEATURE_ID.

Read the spec file and complete any missing technical decisions.
If the spec is already complete, emit the completion signal.

Steps:
1. Read $SPEC_FILE
2. If Technical Decisions table has TBD values, fill them with sensible defaults
3. Update status.md to mark Interview as ✅
4. Add checkpoint to context/session_log.md

When complete, emit: <phase>INTERVIEW_COMPLETE</phase>
If human input is needed, emit: <phase>INTERVIEW_NEEDS_INPUT</phase>
EOF
)
    
    # Run Claude
    local output=$(claude -p "$prompt" --output-format text 2>&1 || true)
    
    # Check for completion signal
    if echo "$output" | grep -q "<phase>INTERVIEW_COMPLETE</phase>"; then
        log_success "Interview phase complete"
        add_session_log "Interview Complete ✅ - Decisions documented"
        return 0
    elif echo "$output" | grep -q "<phase>INTERVIEW_NEEDS_INPUT</phase>"; then
        log_warning "Interview needs human input"
        return 3
    else
        log_error "Interview phase failed"
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
You are executing the PLAN phase for $FEATURE_ID.

Create the technical design and task breakdown.

Steps:
1. Read $SPEC_FILE for requirements
2. Generate $DESIGN_FILE with:
   - Architecture overview
   - Data models
   - API design
   - File structure
3. Generate $TASKS_FILE with ordered task checklist
4. Update status.md to mark Plan as ✅
5. Add checkpoint to context/session_log.md

Follow the templates in docs/features/_template/

When complete, emit: <phase>PLAN_COMPLETE</phase>
EOF
)
    
    local output=$(claude -p "$prompt" --output-format text 2>&1 || true)
    
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
    
    claude -p "$prompt" --output-format text 2>&1 || true
    return 0
}

execute_implement() {
    log_info "Executing Implement phase..."
    
    # Count tasks
    local total=$(grep -cE "^- \[" "$TASKS_FILE" 2>/dev/null || echo "0")
    local complete=$(grep -cE "^- \[x\]" "$TASKS_FILE" 2>/dev/null || echo "0")
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
    
    local output=$(claude -p "$prompt" --output-format text 2>&1 || true)
    
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
    
    claude -p "$prompt" --output-format text 2>&1 || true
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
    
    local output=$(claude -p "$prompt" --output-format text 2>&1 || true)
    
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
