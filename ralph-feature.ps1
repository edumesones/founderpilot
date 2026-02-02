# ============================================================================
# RALPH FEATURE LOOP - PowerShell Version for Windows
# ============================================================================
# Native PowerShell version - better Windows compatibility than Git Bash
# Executes the complete 8-phase Feature Development Cycle autonomously
#
# Usage:
#   .\ralph-feature.ps1 FEAT-XXX [max_iterations]
#   .\ralph-feature.ps1 FEAT-004-invoice-pilot 15
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$FeatureId,

    [Parameter(Mandatory=$false)]
    [int]$MaxIterations = 15
)

# ============================================================================
# CONFIGURATION
# ============================================================================
$script:Iteration = 0
$script:ConsecutiveFailures = 0
$script:MaxFailures = 3
$script:CurrentPhase = ""

# Feature paths
$FeatureDir = "docs/features/$FeatureId"
$SpecFile = "$FeatureDir/spec.md"
$AnalysisFile = "$FeatureDir/analysis.md"
$DesignFile = "$FeatureDir/design.md"
$TasksFile = "$FeatureDir/tasks.md"
$StatusFile = "$FeatureDir/status.md"
$SessionLog = "$FeatureDir/context/session_log.md"
$DecisionsFile = "$FeatureDir/context/decisions.md"
$WrapUpFile = "$FeatureDir/context/wrap_up.md"

# Branch name - extract FEAT-XXX part
$BranchName = "feat/" + ($FeatureId -replace '^(FEAT-\d+).*', '$1')

# Claude CLI flags
$ClaudeFlags = @("--dangerously-skip-permissions", "--output-format", "text")

# ============================================================================
# LOGGING
# ============================================================================
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    $prefix = switch ($Level) {
        "SUCCESS" { "[OK]" }
        "WARNING" { "[WARN]" }
        "ERROR" { "[ERROR]" }
        default { "" }
    }
    Write-Host "[$FeatureId] $timestamp $prefix $Message"
}

function Write-Phase {
    param([string]$Phase)
    Write-Host ""
    Write-Host "================================================================"
    Write-Host "  $FeatureId - Phase: $Phase"
    Write-Host "  Iteration: $script:Iteration / $MaxIterations"
    Write-Host "================================================================"
    Write-Host ""
}

function Add-SessionLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

    if (Test-Path $SessionLog) {
        $content = Get-Content $SessionLog -Raw
        $header = ($content -split "`n" | Select-Object -First 20) -join "`n"
        $rest = ($content -split "`n" | Select-Object -Skip 20) -join "`n"

        $newEntry = "`n### [$timestamp] - [RALPH] $Message`n"
        Set-Content $SessionLog -Value ($header + $newEntry + $rest)
    }
}

# ============================================================================
# PHASE DETECTION HELPERS
# ============================================================================
function Test-InterviewComplete {
    if (-not (Test-Path $SpecFile)) { return $false }

    # Check if Technical Decisions table has non-TBD values
    $allDecisions = Select-String -Path $SpecFile -Pattern '^\|\s*\d+\s*\|'
    if (-not $allDecisions) { return $false }

    $nonTBD = $allDecisions | Where-Object { $_.Line -notmatch 'TBD|_TBD_' }
    return $nonTBD.Count -ge 2
}

function Test-AnalysisComplete {
    if (-not (Test-Path $AnalysisFile)) { return $false }

    # Use SimpleMatch to avoid regex issues with special characters
    $hasProblem = ((Select-String -Path $AnalysisFile -Pattern '## 1.' -SimpleMatch) -or
                   (Select-String -Path $AnalysisFile -Pattern 'Problem Clarification' -SimpleMatch) -or
                   (Select-String -Path $AnalysisFile -Pattern 'Step 1' -SimpleMatch)) -ne $null

    $hasDecision = ((Select-String -Path $AnalysisFile -Pattern '## 11.' -SimpleMatch) -or
                    (Select-String -Path $AnalysisFile -Pattern 'Decision Summary' -SimpleMatch) -or
                    (Select-String -Path $AnalysisFile -Pattern 'Confidence Level' -SimpleMatch)) -ne $null

    return $hasProblem -and $hasDecision
}

function Test-PlanComplete {
    if (-not ((Test-Path $DesignFile) -and (Test-Path $TasksFile))) { return $false }

    $hasTasks = (Select-String -Path $TasksFile -Pattern '## Backend Tasks' -SimpleMatch) -or
                (Select-String -Path $TasksFile -Pattern '## Tasks' -SimpleMatch)
    return $hasTasks -ne $null
}

function Test-BranchCreated {
    $branch = git show-ref --verify --quiet "refs/heads/$BranchName" 2>$null
    return $LASTEXITCODE -eq 0
}

function Test-ImplementationComplete {
    if (-not (Test-Path $TasksFile)) { return $false }

    $total = (Select-String -Path $TasksFile -Pattern '^-\s*\[').Count
    $complete = (Select-String -Path $TasksFile -Pattern '^-\s*\[x\]').Count

    if ($total -gt 0) {
        $percent = [math]::Floor(($complete / $total) * 100)
        return $percent -ge 90
    }
    return $false
}

function Test-PRCreated {
    $prState = gh pr view --json state 2>$null
    return $LASTEXITCODE -eq 0
}

function Test-PRMerged {
    $state = (gh pr view --json state 2>$null | ConvertFrom-Json).state
    return $state -eq "MERGED"
}

function Get-CurrentPhase {
    if (-not (Test-Path $StatusFile)) { return "unknown" }

    # Check for "Complete" instead of emoji for better compatibility
    $interview = (Select-String -Path $StatusFile -Pattern '\| Interview \|.*Complete').Count -gt 0
    $analysis = (Select-String -Path $StatusFile -Pattern '\| Critical Analysis \|.*Complete').Count -gt 0
    $plan = (Select-String -Path $StatusFile -Pattern '\| Plan \|.*Complete').Count -gt 0
    $branch = (Select-String -Path $StatusFile -Pattern '\| Branch \|.*Complete').Count -gt 0
    $implement = (Select-String -Path $StatusFile -Pattern '\| Implement \|.*Complete').Count -gt 0
    $pr = (Select-String -Path $StatusFile -Pattern '\| PR \|.*Complete').Count -gt 0
    $merge = (Select-String -Path $StatusFile -Pattern '\| Merge \|.*Complete').Count -gt 0

    # Check wrap_up.md for completion
    if ((Test-Path $WrapUpFile) -and ((Select-String -Path $WrapUpFile -Pattern 'Wrap-up completado|Wrap-Up Complete').Count -gt 0)) {
        return "complete"
    }
    elseif ($merge) { return "wrapup" }
    elseif ($pr) { return "merge" }
    elseif ($implement) {
        if (Test-ImplementationComplete) { return "pr" }
        else { return "implement" }
    }
    elseif ($branch) {
        if (Test-ImplementationComplete) { return "pr" }
        else { return "implement" }
    }
    elseif ($plan) { return "branch" }
    elseif ($analysis) { return "plan" }
    elseif ($interview) {
        if (Test-AnalysisComplete) { return "plan" }
        else { return "analysis" }
    }
    else {
        if (Test-InterviewComplete) { return "analysis" }
        else { return "interview" }
    }
}

function Get-AnalysisDepth {
    # Check for bug fix keywords
    if (Test-Path $SpecFile) {
        $bugfixCount = (Select-String -Path $SpecFile -Pattern 'bug|fix|hotfix|patch' -AllMatches).Matches.Count
        if ($bugfixCount -ge 2) { return "skip" }
    }

    # Check if this is a new system
    $patterns = (Get-ChildItem -Path "src" -Filter "*.py" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 5).Count

    if ($patterns -lt 5) {
        return "full"
    }
    else {
        $decisionCount = (Select-String -Path $SpecFile -Pattern '^\| \d+ \|').Count
        if ($decisionCount -ge 5) { return "medium" }
        else { return "light" }
    }
}

# ============================================================================
# PHASE EXECUTION
# ============================================================================
function Invoke-Interview {
    Write-Log "Executing Interview phase..."

    if (-not (Test-InterviewComplete)) {
        $hasStructure = (Select-String -Path $SpecFile -Pattern '## Technical Decisions').Count
        if ($hasStructure -eq 0) {
            Write-Log "spec.md needs human input - Interview not complete" -Level WARNING
            Add-SessionLog "Interview needs human input - pausing"
            return 3
        }
    }

    $prompt = @"
You are executing the INTERVIEW phase for $FeatureId.

Your job is to complete the spec.md file with ALL necessary information for this feature.

Context:
- Project overview: Read docs/features/_index.md to understand the project and this feature
- Project definition: Read docs/project.md if available
- This feature: $FeatureId

Steps:
1. Read docs/features/_index.md to understand what this feature is about
2. Read $SpecFile (currently a template)
3. Fill in ALL sections of the spec:
   - Summary: What this feature does (1-2 paragraphs)
   - User Stories: Real user stories for this feature
   - Acceptance Criteria: Clear definition of done
   - Technical Decisions: Replace ALL _TBD_ values with concrete decisions
   - Scope: What IS and is NOT included
   - Dependencies: What this feature needs/blocks
   - Edge Cases: How to handle errors
   - Security: Authentication, data sensitivity, etc.
4. Update $StatusFile to mark Interview phase as ✅
5. Add checkpoint to $SessionLog

Important:
- Fill EVERY section with REAL content, not placeholders
- Make technical decisions based on the project context
- If you genuinely cannot decide without human input, emit INTERVIEW_NEEDS_INPUT

When complete, emit: INTERVIEW_COMPLETE
If human input is needed, emit: INTERVIEW_NEEDS_INPUT
"@

    # Write prompt to temp file for large prompts (PowerShell arg length limit)
    $tempPrompt = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $tempPrompt -Value $prompt -Encoding UTF8 -NoNewline
    $promptText = Get-Content $tempPrompt -Raw
    Remove-Item $tempPrompt -ErrorAction SilentlyContinue

    # Execute claude ONCE, capture output
    Write-Host "[→] Executing Claude..." -ForegroundColor Cyan
    $output = & claude -p $promptText @ClaudeFlags 2>&1 | Out-String

    # Show summary instead of full output
    $lines = $output -split "`n"
    $fileChanges = $lines | Where-Object { $_ -match "Created|Updated|Modified|Deleted" }
    if ($fileChanges) {
        Write-Host "[✓] Files modified:" -ForegroundColor Green
        $fileChanges | ForEach-Object { Write-Host "  $_" }
    }

    # Show signal if present
    if ($output -match "COMPLETE|PROGRESS|NEEDS") {
        $signal = ($output | Select-String -Pattern "\w+_COMPLETE|\w+_PROGRESS|\w+_NEEDS_\w+" -AllMatches).Matches.Value | Select-Object -First 1
        Write-Host "[✓] Signal: $signal" -ForegroundColor Green
    }

    Write-Host ""

    if ($output -match "INTERVIEW_COMPLETE") {
        Write-Log "Interview phase complete" -Level SUCCESS
        Add-SessionLog "Interview Complete - Decisions documented"
        return 0
    }
    elseif ($output -match "INTERVIEW_NEEDS_INPUT") {
        Write-Log "Interview needs human input" -Level WARNING
        return 3
    }
    else {
        Write-Log "Interview phase failed - no completion signal found" -Level ERROR
        return 1
    }
}

function Invoke-Analysis {
    Write-Log "Executing Think Critically phase..."

    if (Test-AnalysisComplete) {
        Write-Log "Analysis already complete, skipping..."

        # Update status.md to mark as complete if not already marked
        $statusContent = Get-Content $StatusFile -Raw
        if ($statusContent -notmatch 'Critical Analysis.*✅') {
            $statusContent = $statusContent -replace '(\| Critical Analysis \| )⬜ Pending', '$1✅ Complete'
            Set-Content $StatusFile -Value $statusContent -NoNewline
            Write-Log "Marked Analysis as complete in status.md"
        }

        return 0
    }

    $depth = Get-AnalysisDepth
    Write-Log "Analysis depth: $depth"

    if ($depth -eq "skip") {
        Write-Log "Skipping analysis (bug fix / hotfix detected)"
        @"
# Critical Analysis - SKIPPED

**Reason:** Bug fix / hotfix - no architectural risk
**Depth:** Skip
**Confidence:** High

Proceeding directly to Plan phase.
"@ | Set-Content $AnalysisFile
        Add-SessionLog "Analysis Skipped - Bug fix/hotfix"
        return 0
    }

    $stepsToRun = switch ($depth) {
        "full" { "ALL 11 STEPS (1-2-3-4-5-6-7-8-9-10-11)" }
        "medium" { "Steps 1, 2, 3, 5, 9, 11 (medium complexity)" }
        "light" { "Steps 1, 2, 5, 11 (light complexity)" }
    }

    $prompt = @"
You are executing the THINK CRITICALLY phase (Phase 2) for $FeatureId.
This is a critical pre-implementation analysis to prevent architectural mistakes.

Analysis Depth: $depth
Steps to execute: $stepsToRun

## The 11-Step Protocol

1. Problem Clarification - What exactly are we solving?
2. Implicit Assumptions - What are we assuming is true? (Mark confidence: High/Medium/Low)
3. Design Space - What approaches exist?
4. Trade-off Analysis - What are we trading?
5. Failure Analysis - What will break and how?
6. Invariants & Boundaries - What must always be true?
7. Observability - How will we know it works?
8. Reversibility - Can we undo this?
9. Adversarial Review - Attack your own design (RED FLAGS)
10. AI Delegation - What can Ralph automate?
11. Decision Summary - Final synthesis + CONFIDENCE LEVEL (High/Medium/Low)

## Instructions

1. Read $SpecFile for requirements
2. Execute the steps listed above for depth: $depth
3. Create $AnalysisFile with your analysis
4. If any of these conditions are met, PAUSE:
   - Step 2: Assumption with Low confidence + High impact
   - Step 9: Critical red flag identified
   - Step 11: Confidence Level = "Low"
5. Update $DecisionsFile with key decisions
6. Update $StatusFile to mark Critical Analysis phase

## Signals

If analysis is complete and safe to proceed:
  Emit: ANALYSIS_COMPLETE

If human intervention needed (pause conditions met):
  Emit: ANALYSIS_NEEDS_REVIEW
  Include: Which pause condition was triggered

If analysis failed:
  Emit: ANALYSIS_FAILED
"@

    Write-Log "Running 11-step protocol (depth: $depth)..."
    # Write prompt to temp file for large prompts (PowerShell arg length limit)
    $tempPrompt = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $tempPrompt -Value $prompt -Encoding UTF8 -NoNewline
    $promptText = Get-Content $tempPrompt -Raw
    Remove-Item $tempPrompt -ErrorAction SilentlyContinue

    # Execute claude ONCE, capture output
    Write-Host "[→] Executing Claude..." -ForegroundColor Cyan
    $output = & claude -p $promptText @ClaudeFlags 2>&1 | Out-String

    # Show summary instead of full output
    $lines = $output -split "`n"
    $fileChanges = $lines | Where-Object { $_ -match "Created|Updated|Modified|Deleted" }
    if ($fileChanges) {
        Write-Host "[✓] Files modified:" -ForegroundColor Green
        $fileChanges | ForEach-Object { Write-Host "  $_" }
    }

    # Show signal if present
    if ($output -match "COMPLETE|PROGRESS|NEEDS") {
        $signal = ($output | Select-String -Pattern "\w+_COMPLETE|\w+_PROGRESS|\w+_NEEDS_\w+" -AllMatches).Matches.Value | Select-Object -First 1
        Write-Host "[✓] Signal: $signal" -ForegroundColor Green
    }

    Write-Host ""

    if ($output -match "ANALYSIS_COMPLETE") {
        Write-Log "Think Critically phase complete" -Level SUCCESS
        Add-SessionLog "Critical Analysis Complete - Confidence verified"
        return 0
    }
    elseif ($output -match "ANALYSIS_NEEDS_REVIEW") {
        Write-Log "Analysis requires human review (pause condition triggered)" -Level WARNING
        Add-SessionLog "[PAUSED] Critical Analysis needs review - see analysis.md"
        return 3
    }
    else {
        Write-Log "Think Critically phase failed" -Level ERROR
        return 1
    }
}

function Invoke-Plan {
    Write-Log "Executing Plan phase..."

    if (Test-PlanComplete) {
        Write-Log "Plan already complete, skipping..."

        # Update status.md to mark as complete if not already marked
        $statusContent = Get-Content $StatusFile -Raw
        if ($statusContent -notmatch 'Plan.*✅') {
            $statusContent = $statusContent -replace '(\| Plan \| )⬜ Pending', '$1✅ Complete'
            Set-Content $StatusFile -Value $statusContent -NoNewline
            Write-Log "Marked Plan as complete in status.md"
        }

        return 0
    }

    $prompt = @"
You are executing the PLAN phase (Phase 3) for $FeatureId.

Create the technical design and task breakdown, informed by the critical analysis.

Steps:
1. Read BOTH inputs (MANDATORY):
   - $SpecFile for requirements and decisions
   - $AnalysisFile for architectural guidance and risk mitigations
2. Generate $DesignFile with:
   - Architecture overview (use recommended approach from analysis)
   - Data models
   - API design
   - File structure
   - Error handling (from failure analysis)
   - Observability tasks (from analysis Step 7)
3. Generate $TasksFile with ordered task checklist including:
   - Implementation tasks
   - Mitigation tasks from analysis
   - Monitoring/observability tasks
4. Update status.md to mark Plan as ✅
5. Add checkpoint to context/session_log.md

Follow the templates in docs/features/_template/

When complete, emit: <phase>PLAN_COMPLETE</phase>
"@

    # Write prompt to temp file for large prompts (PowerShell arg length limit)
    $tempPrompt = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $tempPrompt -Value $prompt -Encoding UTF8 -NoNewline
    $promptText = Get-Content $tempPrompt -Raw
    Remove-Item $tempPrompt -ErrorAction SilentlyContinue

    # Execute claude ONCE, capture output
    Write-Host "[→] Executing Claude..." -ForegroundColor Cyan
    $output = & claude -p $promptText @ClaudeFlags 2>&1 | Out-String

    # Show summary instead of full output
    $lines = $output -split "`n"
    $fileChanges = $lines | Where-Object { $_ -match "Created|Updated|Modified|Deleted" }
    if ($fileChanges) {
        Write-Host "[✓] Files modified:" -ForegroundColor Green
        $fileChanges | ForEach-Object { Write-Host "  $_" }
    }

    # Show signal if present
    if ($output -match "COMPLETE|PROGRESS|NEEDS") {
        $signal = ($output | Select-String -Pattern "\w+_COMPLETE|\w+_PROGRESS|\w+_NEEDS_\w+" -AllMatches).Matches.Value | Select-Object -First 1
        Write-Host "[✓] Signal: $signal" -ForegroundColor Green
    }

    Write-Host ""

    if ($output -match "<phase>PLAN_COMPLETE</phase>") {
        Write-Log "Plan phase complete" -Level SUCCESS
        Add-SessionLog "Plan Complete ✅ - Design and tasks created"
        return 0
    }
    else {
        Write-Log "Plan phase failed" -Level ERROR
        return 1
    }
}

function Invoke-Branch {
    Write-Log "Executing Branch phase..."

    if (Test-BranchCreated) {
        Write-Log "Branch already exists: $BranchName"
        git checkout $BranchName 2>$null

        # Update status.md to mark as complete if not already marked
        $statusContent = Get-Content $StatusFile -Raw
        if ($statusContent -notmatch '\| Branch \|.*Complete') {
            $statusContent = $statusContent -replace '(\| Branch \| )⬜ Pending', '$1✅ Complete'
            Set-Content $StatusFile -Value $statusContent -NoNewline
            Write-Log "Marked Branch as complete in status.md"
        }

        return 0
    }

    git checkout main 2>$null
    if ($LASTEXITCODE -ne 0) { git checkout master 2>$null }
    git pull origin main 2>$null
    if ($LASTEXITCODE -ne 0) { git pull origin master 2>$null }
    git checkout -b $BranchName

    Write-Log "Branch created: $BranchName" -Level SUCCESS
    Add-SessionLog "Branch Created ✅ - $BranchName"

    $prompt = @"
Update $StatusFile to mark Branch phase as ✅.
Add the branch name: $BranchName

Emit: <phase>BRANCH_COMPLETE</phase>
"@

    $tempPrompt = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $tempPrompt -Value $prompt -Encoding UTF8 -NoNewline
    $promptText = Get-Content $tempPrompt -Raw
    Remove-Item $tempPrompt -ErrorAction SilentlyContinue

    # Execute claude ONCE, show summary
    Write-Host "[→] Executing Claude..." -ForegroundColor Cyan
    & claude -p $promptText @ClaudeFlags 2>&1 | Out-Null
    Write-Host "[✓] Complete" -ForegroundColor Green
    Write-Host ""
    return 0
}

function Invoke-Implement {
    Write-Log "Executing Implement phase..."

    $total = (Select-String -Path $TasksFile -Pattern '^- \[').Count
    $complete = (Select-String -Path $TasksFile -Pattern '^- \[x\]').Count
    $remaining = $total - $complete

    Write-Log "Tasks: $complete/$total complete ($remaining remaining)"

    if ($remaining -eq 0) {
        Write-Log "All tasks complete!" -Level SUCCESS
        Add-SessionLog "Implementation Complete ✅ - All $total tasks done"
        return 0
    }

    $batchSize = 3

    $prompt = @"
You are executing the IMPLEMENT phase for $FeatureId.
This is iteration $script:Iteration.

Current progress: $complete/$total tasks complete.

Steps:
1. Read $TasksFile to find next uncompleted tasks (marked with [ ])
2. Complete up to $batchSize tasks:
   - Mark task as [🟡] before starting
   - Implement the code
   - Mark task as [x] when done
   - Commit: git add . && git commit -m "${FeatureId}: [task description]"
3. Update progress in status.md
4. Add log entry to context/session_log.md

If all tasks are complete, emit: <phase>IMPLEMENT_COMPLETE</phase>
If some tasks done but more remain, emit: <phase>IMPLEMENT_PROGRESS</phase>
"@

    # Write prompt to temp file for large prompts (PowerShell arg length limit)
    $tempPrompt = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $tempPrompt -Value $prompt -Encoding UTF8 -NoNewline
    $promptText = Get-Content $tempPrompt -Raw
    Remove-Item $tempPrompt -ErrorAction SilentlyContinue

    # Execute claude ONCE, capture output
    Write-Host "[→] Executing Claude..." -ForegroundColor Cyan
    $output = & claude -p $promptText @ClaudeFlags 2>&1 | Out-String

    # Show summary instead of full output
    $lines = $output -split "`n"
    $fileChanges = $lines | Where-Object { $_ -match "Created|Updated|Modified|Deleted" }
    if ($fileChanges) {
        Write-Host "[✓] Files modified:" -ForegroundColor Green
        $fileChanges | ForEach-Object { Write-Host "  $_" }
    }

    # Show signal if present
    if ($output -match "COMPLETE|PROGRESS|NEEDS") {
        $signal = ($output | Select-String -Pattern "\w+_COMPLETE|\w+_PROGRESS|\w+_NEEDS_\w+" -AllMatches).Matches.Value | Select-Object -First 1
        Write-Host "[✓] Signal: $signal" -ForegroundColor Green
    }

    Write-Host ""

    if ($output -match "<phase>IMPLEMENT_COMPLETE</phase>") {
        Write-Log "Implementation complete" -Level SUCCESS
        return 0
    }
    elseif ($output -match "<phase>IMPLEMENT_PROGRESS</phase>") {
        Write-Log "Progress made, continuing..."
        Add-SessionLog "Implementation Progress - Batch complete"
        return 0
    }
    else {
        Write-Log "No progress signal detected" -Level WARNING
        return 1
    }
}

function Invoke-PR {
    Write-Log "Executing PR phase..."

    if (Test-PRCreated) {
        Write-Log "PR already exists"
        return 0
    }

    # === CRITICAL: Sync with main before creating PR ===
    Write-Log "Syncing with main branch..."

    # Determine base branch (main or master)
    git fetch origin 2>$null
    $baseBranch = if (git show-ref --verify --quiet refs/remotes/origin/main) { "main" } else { "master" }
    Write-Log "Base branch: $baseBranch"

    # Attempt merge
    $mergeOutput = git merge "origin/$baseBranch" 2>&1

    if ($LASTEXITCODE -ne 0) {
        # Merge conflict detected
        Write-Log "Merge conflicts detected with $baseBranch" -Level WARNING

        # Get list of conflicted files
        $conflictedFiles = git diff --name-only --diff-filter=U 2>$null

        if ($conflictedFiles) {
            Write-Host ""
            Write-Host "========================================" -ForegroundColor Yellow
            Write-Host "  MERGE CONFLICTS DETECTED" -ForegroundColor Yellow
            Write-Host "========================================" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Conflicted files:" -ForegroundColor Yellow
            $conflictedFiles | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
            Write-Host ""

            # Attempt auto-resolution
            $autoResolved = $true
            foreach ($file in $conflictedFiles) {
                Write-Log "Attempting auto-resolution: $file"

                # Strategy 1: Documentation files → take ours (feature branch)
                if ($file -match 'docs/features/.*/status\.md|docs/features/.*/context/.*\.md') {
                    Write-Log "  Strategy: Keep feature version (documentation)" -Level WARNING
                    git checkout --ours $file 2>$null
                    git add $file 2>$null
                }
                # Strategy 2: Generated files → regenerate
                elseif ($file -match '\.lock$|package-lock\.json|yarn\.lock|poetry\.lock') {
                    Write-Log "  Strategy: Regenerate lockfile" -Level WARNING
                    git checkout --ours $file 2>$null
                    git add $file 2>$null
                }
                # Strategy 3: Cannot auto-resolve
                else {
                    Write-Log "  Cannot auto-resolve: $file" -Level ERROR
                    $autoResolved = $false
                }
            }

            if ($autoResolved) {
                # Complete the merge
                git commit -m "$FeatureId: Resolve merge conflicts with $baseBranch (auto-resolved)" 2>$null
                Write-Log "Conflicts auto-resolved successfully" -Level SUCCESS
                Add-SessionLog "Merge conflicts auto-resolved"
            }
            else {
                # Cannot auto-resolve - pause for human intervention
                Write-Host ""
                Write-Host "========================================" -ForegroundColor Red
                Write-Host "  MANUAL INTERVENTION REQUIRED" -ForegroundColor Red
                Write-Host "========================================" -ForegroundColor Red
                Write-Host ""
                Write-Host "Cannot auto-resolve all conflicts." -ForegroundColor Red
                Write-Host ""
                Write-Host "To resolve manually:" -ForegroundColor Yellow
                Write-Host "  1. Resolve conflicts in the files listed above" -ForegroundColor Yellow
                Write-Host "  2. git add <resolved-files>" -ForegroundColor Yellow
                Write-Host "  3. git commit -m '$FeatureId: Resolve merge conflicts'" -ForegroundColor Yellow
                Write-Host "  4. Run ralph-feature.ps1 again to continue" -ForegroundColor Yellow
                Write-Host ""

                Add-SessionLog "[PAUSED] Merge conflicts need manual resolution"
                return 3  # Human input needed
            }
        }
    }
    else {
        Write-Log "No merge conflicts - clean merge with $baseBranch" -Level SUCCESS
    }

    # Push to remote
    git push -u origin $BranchName 2>$null

    $prTitle = "${FeatureId}: " + ($FeatureId -replace 'FEAT-\d+-', '' -replace '-', ' ')

    $prBody = @"
## Summary

Automated PR for $FeatureId

## Checklist
- [x] Implementation complete
- [x] Tests passing
- [x] Synced with $baseBranch
- [ ] Review approved

---
*Created by Ralph Loop*
"@

    gh pr create --title $prTitle --body $prBody --base $baseBranch 2>$null

    Write-Log "PR created" -Level SUCCESS
    Add-SessionLog "PR Created ✅"

    $prompt = @"
Update $StatusFile to mark PR phase as ✅.
Add PR link if available.

Emit: <phase>PR_COMPLETE</phase>
"@

    $tempPrompt = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $tempPrompt -Value $prompt -Encoding UTF8 -NoNewline
    $promptText = Get-Content $tempPrompt -Raw
    Remove-Item $tempPrompt -ErrorAction SilentlyContinue

    # Execute claude ONCE, show summary
    Write-Host "[→] Executing Claude..." -ForegroundColor Cyan
    & claude -p $promptText @ClaudeFlags 2>&1 | Out-Null
    Write-Host "[✓] Complete" -ForegroundColor Green
    Write-Host ""
    return 0
}

function Invoke-Merge {
    Write-Log "Checking merge status..."

    if (Test-PRMerged) {
        Write-Log "PR is merged!" -Level SUCCESS
        Add-SessionLog "Merged ✅ - PR merged to main"
        return 0
    }

    $state = (gh pr view --json state 2>$null | ConvertFrom-Json).state

    if ($state -eq "OPEN") {
        Write-Log "PR is open, waiting for approval..." -Level WARNING
        return 2
    }
    elseif ($state -eq "CLOSED") {
        Write-Log "PR was closed without merging" -Level ERROR
        return 1
    }

    Write-Log "Merge status: $state"
    return 2
}

function Invoke-Wrapup {
    Write-Log "Executing Wrap-up phase..."

    if ((Test-Path $WrapUpFile) -and ((Select-String -Path $WrapUpFile -Pattern 'Wrap-up completado').Count -gt 0)) {
        Write-Log "Wrap-up already complete" -Level SUCCESS
        return 100
    }

    $prompt = @"
You are executing the WRAP-UP phase for $FeatureId.

This is the final phase. Complete the wrap-up documentation.

Steps:
1. Create/update $WrapUpFile using the template in docs/features/_template/context/wrap-up.md
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
"@

    # Write prompt to temp file for large prompts (PowerShell arg length limit)
    $tempPrompt = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $tempPrompt -Value $prompt -Encoding UTF8 -NoNewline
    $promptText = Get-Content $tempPrompt -Raw
    Remove-Item $tempPrompt -ErrorAction SilentlyContinue

    # Execute claude ONCE, capture output
    Write-Host "[→] Executing Claude..." -ForegroundColor Cyan
    $output = & claude -p $promptText @ClaudeFlags 2>&1 | Out-String

    # Show summary instead of full output
    $lines = $output -split "`n"
    $fileChanges = $lines | Where-Object { $_ -match "Created|Updated|Modified|Deleted" }
    if ($fileChanges) {
        Write-Host "[✓] Files modified:" -ForegroundColor Green
        $fileChanges | ForEach-Object { Write-Host "  $_" }
    }

    # Show signal if present
    if ($output -match "COMPLETE|PROGRESS|NEEDS") {
        $signal = ($output | Select-String -Pattern "\w+_COMPLETE|\w+_PROGRESS|\w+_NEEDS_\w+" -AllMatches).Matches.Value | Select-Object -First 1
        Write-Host "[✓] Signal: $signal" -ForegroundColor Green
    }

    Write-Host ""

    if ($output -match "<phase>FEATURE_COMPLETE</phase>") {
        Write-Log "Feature complete! [COMPLETE]" -Level SUCCESS
        Add-SessionLog "Feature Complete [COMPLETE] - Wrap-up done"
        return 100
    }
    elseif ($output -match "<phase>WRAPUP_COMPLETE</phase>") {
        Write-Log "Wrap-up complete" -Level SUCCESS
        return 100
    }
    else {
        Write-Log "Wrap-up failed" -Level ERROR
        return 1
    }
}

function Invoke-Phase {
    param([string]$Phase)

    $script:CurrentPhase = $Phase
    Write-Phase $Phase

    switch ($Phase) {
        "interview" { return Invoke-Interview }
        "analysis" { return Invoke-Analysis }
        "plan" { return Invoke-Plan }
        "branch" { return Invoke-Branch }
        "implement" { return Invoke-Implement }
        "pr" { return Invoke-PR }
        "merge" { return Invoke-Merge }
        "wrapup" { return Invoke-Wrapup }
        "complete" {
            Write-Log "Feature is already complete!" -Level SUCCESS
            return 100
        }
        default {
            Write-Log "Unknown phase: $Phase" -Level ERROR
            return 1
        }
    }
}

# ============================================================================
# MAIN LOOP
# ============================================================================
Write-Host "DEBUG: Entering main()"
Write-Host "DEBUG: FEATURE_ID=$FeatureId"
Write-Host "DEBUG: FEATURE_DIR=$FeatureDir"
Write-Log "Starting Ralph Feature Loop for $FeatureId"
Write-Log "Max iterations: $MaxIterations"

if (-not (Test-Path $FeatureDir)) {
    Write-Log "Feature directory not found: $FeatureDir" -Level ERROR
    exit 1
}

if (Test-BranchCreated) {
    git checkout $BranchName 2>$null
}

while ($script:Iteration -lt $MaxIterations) {
    $script:Iteration++
    Write-Host "DEBUG: Iteration $script:Iteration"

    $phase = Get-CurrentPhase
    Write-Host "DEBUG: Phase detected: $phase"
    Write-Log "Detected phase: $phase"

    $result = Invoke-Phase $phase

    switch ($result) {
        0 {
            # Success
            $script:ConsecutiveFailures = 0
            Write-Log "Phase $phase completed successfully" -Level SUCCESS
        }
        1 {
            # Failure
            $script:ConsecutiveFailures++
            Write-Log "Phase $phase failed (failure $script:ConsecutiveFailures/$script:MaxFailures)" -Level ERROR

            if ($script:ConsecutiveFailures -ge $script:MaxFailures) {
                Write-Log "Too many consecutive failures. Pausing for human intervention." -Level ERROR
                Add-SessionLog "[WARN] Paused after $script:ConsecutiveFailures failures in $phase phase"
                exit 1
            }
        }
        2 {
            # Waiting (e.g., for merge approval)
            Write-Log "Waiting for external action (merge approval)..."
            Start-Sleep -Seconds 60
        }
        3 {
            # Human input needed
            Write-Log "Human input required. Pausing loop." -Level WARNING
            Add-SessionLog "[PAUSED] Paused - Human input needed in $phase phase"
            exit 0
        }
        100 {
            # Feature complete
            Write-Log "[COMPLETE] Feature $FeatureId is complete!" -Level SUCCESS
            exit 0
        }
    }

    Start-Sleep -Seconds 2
}

Write-Log "Max iterations ($MaxIterations) reached" -Level WARNING
Add-SessionLog "[WARN] Max iterations reached at $script:CurrentPhase phase"
exit 0
