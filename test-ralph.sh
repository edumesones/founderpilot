#!/bin/bash
echo "Step 1: Start"
FEATURE_ID="FEAT-005-meeting-pilot"
echo "Step 2: Variable set to $FEATURE_ID"

log_info() {
    echo "[$FEATURE_ID] $(date +%H:%M:%S) - $1"
}

echo "Step 3: Function defined"
log_info "Testing log function"
echo "Step 4: Done"
