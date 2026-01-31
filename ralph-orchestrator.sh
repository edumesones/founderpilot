#!/bin/bash
# ============================================================================
# RALPH ORCHESTRATOR - Multi-Feature Autonomous Development
# ============================================================================
# Manages multiple features in parallel using git worktrees
# Integrates with Feature Development Cycle v2.0 (7 phases)
#
# Usage:
#   ./ralph-orchestrator.sh [max_parallel]
#   ./ralph-orchestrator.sh 3              # Run up to 3 features in parallel
#   ./ralph-orchestrator.sh --status       # Show current status
#   ./ralph-orchestrator.sh --stop         # Stop all loops gracefully
# ============================================================================

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================
MAX_PARALLEL=${1:-3}
POLL_INTERVAL=30
STATE_FILE="feature-loop-state.json"
ACTIVITY_LOG="activity.md"
FEATURES_INDEX="docs/features/_index.md"
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
REPO_NAME=$(basename "$REPO_ROOT")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_activity() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "- **[$timestamp]** $message" >> "$ACTIVITY_LOG"
}

# ============================================================================
# STATE MANAGEMENT (using Python for JSON)
# ============================================================================
init_state() {
    if [[ ! -f "$STATE_FILE" ]]; then
        cat > "$STATE_FILE" << 'EOF'
{
    "orchestrator": {
        "status": "idle",
        "started_at": null,
        "max_parallel": 3,
        "pid": null
    },
    "features": {},
    "completed": [],
    "failed": []
}
EOF
        log_info "State file initialized: $STATE_FILE"
    fi
}

update_orchestrator_state() {
    local status="$1"
    local pid="$$"
    local started_at=$(date -Iseconds)
    
    python3 << EOF
import json
with open('$STATE_FILE', 'r') as f:
    state = json.load(f)
state['orchestrator']['status'] = '$status'
state['orchestrator']['pid'] = $pid
state['orchestrator']['started_at'] = '$started_at'
state['orchestrator']['max_parallel'] = $MAX_PARALLEL
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
EOF
}

update_feature_state() {
    local feature_id="$1"
    local status="$2"
    local phase="$3"
    local worktree="$4"
    local pid="$5"
    
    python3 << EOF
import json
from datetime import datetime
with open('$STATE_FILE', 'r') as f:
    state = json.load(f)
if '$feature_id' not in state['features']:
    state['features']['$feature_id'] = {
        'status': '$status',
        'phase': '$phase',
        'iterations': 0,
        'failures': 0,
        'worktree': '$worktree',
        'pid': $pid if '$pid' else None,
        'started_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
else:
    state['features']['$feature_id']['status'] = '$status'
    state['features']['$feature_id']['phase'] = '$phase'
    state['features']['$feature_id']['updated_at'] = datetime.now().isoformat()
    if '$worktree':
        state['features']['$feature_id']['worktree'] = '$worktree'
    if '$pid':
        state['features']['$feature_id']['pid'] = $pid
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
EOF
}

mark_feature_complete() {
    local feature_id="$1"
    
    python3 << EOF
import json
with open('$STATE_FILE', 'r') as f:
    state = json.load(f)
if '$feature_id' in state['features']:
    del state['features']['$feature_id']
if '$feature_id' not in state['completed']:
    state['completed'].append('$feature_id')
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
EOF
}

get_active_count() {
    python3 << EOF
import json
with open('$STATE_FILE', 'r') as f:
    state = json.load(f)
count = len([f for f in state['features'].values() if f['status'] == 'running'])
print(count)
EOF
}

get_feature_status() {
    local feature_id="$1"
    python3 << EOF
import json
with open('$STATE_FILE', 'r') as f:
    state = json.load(f)
if '$feature_id' in state['features']:
    print(state['features']['$feature_id']['status'])
else:
    print('unknown')
EOF
}

# ============================================================================
# FEATURE DISCOVERY
# ============================================================================
get_pending_features() {
    # Read _index.md and extract features with ⚪ Pending status
    if [[ ! -f "$FEATURES_INDEX" ]]; then
        log_warning "Features index not found: $FEATURES_INDEX"
        return
    fi
    
    # Extract FEAT-XXX from lines containing ⚪ Pending
    grep -E '\|\s*FEAT-[0-9]+-' "$FEATURES_INDEX" | \
        grep -E '⚪|Pending' | \
        grep -oE 'FEAT-[0-9]+-[a-zA-Z0-9_-]+' | \
        head -n "$MAX_PARALLEL"
}

# ============================================================================
# WORKTREE MANAGEMENT
# ============================================================================
create_worktree() {
    local feature_id="$1"
    local worktree_path="$REPO_ROOT/../${REPO_NAME}-${feature_id}-loop"
    local branch_name=$(echo "$feature_id" | sed 's/FEAT-/feature\//' | tr '[:upper:]' '[:lower:]')
    
    # Check if worktree already exists
    if [[ -d "$worktree_path" ]]; then
        log_info "Worktree already exists: $worktree_path"
        echo "$worktree_path"
        return 0
    fi
    
    # Create branch if it doesn't exist
    if ! git show-ref --verify --quiet "refs/heads/$branch_name"; then
        log_info "Creating branch: $branch_name"
        git branch "$branch_name" main 2>/dev/null || git branch "$branch_name" master
    fi
    
    # Create worktree
    log_info "Creating worktree: $worktree_path"
    git worktree add "$worktree_path" "$branch_name"
    
    echo "$worktree_path"
}

remove_worktree() {
    local worktree_path="$1"
    
    if [[ -d "$worktree_path" ]]; then
        log_info "Removing worktree: $worktree_path"
        git worktree remove "$worktree_path" --force 2>/dev/null || true
    fi
}

# ============================================================================
# MERGE DETECTION
# ============================================================================
is_feature_merged() {
    local feature_id="$1"
    local branch_name=$(echo "$feature_id" | sed 's/FEAT-/feature\//' | tr '[:upper:]' '[:lower:]')
    
    # Fetch latest
    git fetch origin --quiet 2>/dev/null || true
    
    # Check if branch is merged into main
    if git branch --merged main 2>/dev/null | grep -q "$branch_name"; then
        return 0
    fi
    if git branch --merged master 2>/dev/null | grep -q "$branch_name"; then
        return 0
    fi
    
    return 1
}

# ============================================================================
# FEATURE LOOP LAUNCHER
# ============================================================================
launch_feature_loop() {
    local feature_id="$1"
    local max_iterations="${2:-15}"
    
    # Create worktree
    local worktree_path=$(create_worktree "$feature_id")
    if [[ -z "$worktree_path" ]]; then
        log_error "Failed to create worktree for $feature_id"
        return 1
    fi
    
    # Update state
    update_feature_state "$feature_id" "running" "starting" "$worktree_path" "0"
    
    # Launch the feature loop in background
    log_info "Launching feature loop for $feature_id in $worktree_path"
    log_activity "🚀 Started loop for **$feature_id** (worktree: $worktree_path)"
    
    (
        cd "$worktree_path"
        ./ralph-feature.sh "$feature_id" "$max_iterations" 2>&1 | \
            tee -a "ralph-${feature_id}.log"
    ) &
    
    local pid=$!
    update_feature_state "$feature_id" "running" "started" "$worktree_path" "$pid"
    
    log_success "Feature loop started: $feature_id (PID: $pid)"
}

# ============================================================================
# UPDATE INDEX STATUS
# ============================================================================
update_index_status() {
    local feature_id="$1"
    local new_status="$2"  # ⚪ Pending, 🟡 In Progress, 🟢 Complete, etc.
    
    if [[ -f "$FEATURES_INDEX" ]]; then
        # This is a simplified update - in production, use Python for proper parsing
        log_info "Updating $feature_id status to $new_status in _index.md"
    fi
}

# ============================================================================
# MAIN ORCHESTRATION LOOP
# ============================================================================
orchestrate() {
    log_info "Starting Ralph Orchestrator (max parallel: $MAX_PARALLEL)"
    log_activity "🎭 **Orchestrator started** (max parallel: $MAX_PARALLEL)"
    
    init_state
    update_orchestrator_state "running"
    
    while true; do
        # Check for pending features
        local pending=$(get_pending_features)
        local active_count=$(get_active_count)
        
        # Launch new features if capacity available
        for feature_id in $pending; do
            if [[ $active_count -ge $MAX_PARALLEL ]]; then
                break
            fi
            
            local status=$(get_feature_status "$feature_id")
            if [[ "$status" == "unknown" ]]; then
                log_info "Found pending feature: $feature_id"
                launch_feature_loop "$feature_id"
                ((active_count++))
            fi
        done
        
        # Check for merged features
        python3 << 'EOF'
import json
with open('feature-loop-state.json', 'r') as f:
    state = json.load(f)
for feature_id in list(state['features'].keys()):
    print(feature_id)
EOF
        local active_features=$(python3 -c "
import json
with open('$STATE_FILE', 'r') as f:
    state = json.load(f)
for fid in state['features'].keys():
    print(fid)
")
        
        for feature_id in $active_features; do
            if is_feature_merged "$feature_id"; then
                log_success "Feature merged: $feature_id"
                log_activity "✅ **$feature_id** merged to main"
                
                # Get worktree path and clean up
                local worktree=$(python3 -c "
import json
with open('$STATE_FILE', 'r') as f:
    state = json.load(f)
print(state['features'].get('$feature_id', {}).get('worktree', ''))
")
                
                if [[ -n "$worktree" ]]; then
                    remove_worktree "$worktree"
                fi
                
                mark_feature_complete "$feature_id"
                update_index_status "$feature_id" "🟢 Complete"
            fi
        done
        
        # Check if all features are complete
        active_count=$(get_active_count)
        if [[ $active_count -eq 0 ]] && [[ -z "$pending" ]]; then
            log_success "All features complete!"
            log_activity "🎉 **All features complete** - Orchestrator idle"
            update_orchestrator_state "complete"
            break
        fi
        
        # Wait before next poll
        sleep $POLL_INTERVAL
    done
}

# ============================================================================
# STATUS DISPLAY
# ============================================================================
show_status() {
    if [[ ! -f "$STATE_FILE" ]]; then
        echo "No state file found. Orchestrator has not been run yet."
        return
    fi
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║              RALPH ORCHESTRATOR STATUS                           ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    python3 << 'EOF'
import json
from datetime import datetime

with open('feature-loop-state.json', 'r') as f:
    state = json.load(f)

# Orchestrator status
orch = state['orchestrator']
print(f"Orchestrator: {orch['status'].upper()}")
print(f"  PID: {orch.get('pid', 'N/A')}")
print(f"  Max Parallel: {orch.get('max_parallel', 3)}")
print(f"  Started: {orch.get('started_at', 'N/A')}")
print()

# Active features
print("Active Features:")
print("-" * 60)
if state['features']:
    for fid, data in state['features'].items():
        print(f"  {fid}:")
        print(f"    Status: {data['status']}")
        print(f"    Phase: {data['phase']}")
        print(f"    Iterations: {data['iterations']}")
        print(f"    Failures: {data['failures']}")
        print(f"    Worktree: {data.get('worktree', 'N/A')}")
        print()
else:
    print("  (none)")
print()

# Completed
print(f"Completed: {len(state['completed'])}")
for fid in state['completed']:
    print(f"  ✅ {fid}")
print()

# Failed
print(f"Failed: {len(state['failed'])}")
for fid in state['failed']:
    print(f"  ❌ {fid}")
EOF
    echo ""
}

# ============================================================================
# STOP ORCHESTRATOR
# ============================================================================
stop_orchestrator() {
    log_warning "Stopping orchestrator..."
    
    if [[ -f "$STATE_FILE" ]]; then
        # Kill all feature loop processes
        python3 << 'EOF'
import json
import os
import signal

with open('feature-loop-state.json', 'r') as f:
    state = json.load(f)

# Kill feature loop processes
for fid, data in state['features'].items():
    pid = data.get('pid')
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped {fid} (PID: {pid})")
        except ProcessLookupError:
            print(f"{fid} already stopped")

# Update orchestrator status
state['orchestrator']['status'] = 'stopped'
with open('feature-loop-state.json', 'w') as f:
    json.dump(state, f, indent=2)
EOF
        
        log_activity "⏹️ **Orchestrator stopped** by user"
    fi
    
    log_success "Orchestrator stopped"
}

# ============================================================================
# MAIN
# ============================================================================
case "${1:-}" in
    --status)
        show_status
        ;;
    --stop)
        stop_orchestrator
        ;;
    --help|-h)
        echo "Ralph Orchestrator - Multi-Feature Autonomous Development"
        echo ""
        echo "Usage:"
        echo "  ./ralph-orchestrator.sh [max_parallel]   Start orchestrator"
        echo "  ./ralph-orchestrator.sh --status         Show current status"
        echo "  ./ralph-orchestrator.sh --stop           Stop all loops"
        echo ""
        echo "Examples:"
        echo "  ./ralph-orchestrator.sh 3                Run up to 3 features"
        echo "  ./ralph-orchestrator.sh 1                Run 1 feature at a time"
        ;;
    *)
        # Initialize activity log if needed
        if [[ ! -f "$ACTIVITY_LOG" ]]; then
            echo "# Ralph Loop Activity Log" > "$ACTIVITY_LOG"
            echo "" >> "$ACTIVITY_LOG"
            echo "Chronological log of all autonomous loop actions." >> "$ACTIVITY_LOG"
            echo "" >> "$ACTIVITY_LOG"
            echo "---" >> "$ACTIVITY_LOG"
            echo "" >> "$ACTIVITY_LOG"
        fi
        
        orchestrate
        ;;
esac
