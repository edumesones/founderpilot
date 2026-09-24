#!/usr/bin/env python3
"""
Fork Feature with Git Worktree - Isolated parallel development.

Creates a new git worktree for each fork, ensuring complete isolation
and zero conflicts during parallel development.

Usage:
    python fork_feature.py FEAT-001-auth backend
    python fork_feature.py FEAT-001-auth full
    python fork_feature.py --list-roles
    python fork_feature.py --list-worktrees
    python fork_feature.py --cleanup FEAT-001-auth

Worktree structure:
    proyecto/                          <- Main repo
    proyecto-FEAT-001-auth-backend/    <- Worktree for backend
    proyecto-FEAT-001-auth-frontend/   <- Worktree for frontend
    proyecto-FEAT-001-auth-full/       <- Worktree for full feature
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


# =============================================================================
# ROLE DEFINITIONS
# =============================================================================

ROLES = {
    "backend": {
        "name": "Backend Developer",
        "focus": "Python backend: FastAPI routes, SQLAlchemy models, services, business logic",
        "tasks_section": "Backend",
        "files_pattern": "src/api/, src/models/, src/services/, src/utils/",
        "do_not_touch": "Frontend components, UI files, React/Gradio code"
    },
    "frontend": {
        "name": "Frontend Developer", 
        "focus": "UI code: React components, Gradio interfaces, styling, user interactions",
        "tasks_section": "Frontend",
        "files_pattern": "src/components/, src/ui/, src/pages/, static/",
        "do_not_touch": "Backend API code, database models, services"
    },
    "data": {
        "name": "Data Engineer",
        "focus": "Data pipelines, ML models, preprocessing, transformations",
        "tasks_section": "Data",
        "files_pattern": "src/data/, src/ml/, src/pipelines/",
        "do_not_touch": "API endpoints, UI components"
    },
    "tests": {
        "name": "Test Engineer",
        "focus": "Unit tests, integration tests, e2e tests, test fixtures",
        "tasks_section": "Tests",
        "files_pattern": "tests/",
        "do_not_touch": "Production code (only read it to understand what to test)"
    },
    "docs": {
        "name": "Documentation Specialist",
        "focus": "README, docstrings, API documentation, user guides",
        "tasks_section": "Documentation",
        "files_pattern": "docs/, README.md, *.md",
        "do_not_touch": "Production code (only read it to document)"
    },
    "full": {
        "name": "Full Stack Developer",
        "focus": "All tasks in order as defined in tasks.md",
        "tasks_section": "ALL",
        "files_pattern": "src/, tests/",
        "do_not_touch": "Nothing - you handle everything"
    }
}


# =============================================================================
# GIT WORKTREE FUNCTIONS
# =============================================================================

def run_git(args: list, cwd: str = None) -> tuple:
    """Run a git command and return (success, output)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        output = result.stdout.strip() + result.stderr.strip()
        return result.returncode == 0, output
    except Exception as e:
        return False, str(e)


def get_repo_root() -> Path:
    """Get the root of the git repository."""
    success, output = run_git(["rev-parse", "--show-toplevel"])
    if success:
        return Path(output.strip())
    return Path.cwd()


def get_current_branch() -> str:
    """Get the current git branch."""
    success, output = run_git(["branch", "--show-current"])
    return output.strip() if success else "main"


def get_worktree_path(feature_id: str, role: str) -> Path:
    """Generate the worktree path for a feature/role combination."""
    repo_root = get_repo_root()
    repo_name = repo_root.name
    worktree_name = f"{repo_name}-{feature_id}-{role}"
    return repo_root.parent / worktree_name


def get_branch_name(feature_id: str) -> str:
    """Generate the branch name for a feature."""
    # Extract number and name from FEAT-001-auth format
    parts = feature_id.lower().replace("feat-", "").split("-", 1)
    if len(parts) == 2:
        return f"feature/{parts[0]}-{parts[1]}"
    return f"feature/{feature_id.lower()}"


def branch_exists(branch_name: str) -> bool:
    """Check if a branch exists locally or remotely."""
    success_local, _ = run_git(["show-ref", "--verify", f"refs/heads/{branch_name}"])
    success_remote, _ = run_git(["show-ref", "--verify", f"refs/remotes/origin/{branch_name}"])
    return success_local or success_remote


def create_worktree(feature_id: str, role: str) -> tuple:
    """
    Create a git worktree for the feature/role.
    
    Returns: (success, worktree_path, message)
    """
    repo_root = get_repo_root()
    worktree_path = get_worktree_path(feature_id, role)
    branch_name = get_branch_name(feature_id)
    
    # Check if worktree already exists
    if worktree_path.exists():
        return True, worktree_path, f"Worktree already exists at {worktree_path}"
    
    # Check if branch exists, if not create it from main
    if not branch_exists(branch_name):
        print(f"📌 Creating branch {branch_name} from main...")
        
        # Make sure we're up to date
        run_git(["fetch", "origin"])
        
        # Create branch from main/master
        success, output = run_git(["branch", branch_name, "main"])
        if not success:
            # Try master if main doesn't exist
            success, output = run_git(["branch", branch_name, "master"])
        
        if not success:
            return False, worktree_path, f"Failed to create branch: {output}"
        
        print(f"✅ Branch {branch_name} created")
    
    # Create worktree
    print(f"📁 Creating worktree at {worktree_path}...")
    success, output = run_git(["worktree", "add", str(worktree_path), branch_name])
    
    if not success:
        return False, worktree_path, f"Failed to create worktree: {output}"
    
    return True, worktree_path, f"Worktree created at {worktree_path}"


def list_worktrees() -> list:
    """List all git worktrees."""
    success, output = run_git(["worktree", "list", "--porcelain"])
    if not success:
        return []
    
    worktrees = []
    current = {}
    
    for line in output.split("\n"):
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:]}
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:]
        elif line == "bare":
            current["bare"] = True
    
    if current:
        worktrees.append(current)
    
    return worktrees


def remove_worktree(worktree_path: Path) -> tuple:
    """Remove a git worktree."""
    success, output = run_git(["worktree", "remove", str(worktree_path), "--force"])
    return success, output


# =============================================================================
# CONTEXT BUILDING
# =============================================================================

def read_file_safe(path: Path) -> str:
    """Read file content or return placeholder."""
    if path.exists():
        return path.read_text(encoding='utf-8')
    return f"[File not found: {path}]"


def build_context_prompt(feature_id: str, role_id: str, worktree_path: Path) -> str:
    """Build the full context prompt for the fork."""
    
    role = ROLES[role_id]
    feature_path = worktree_path / "docs" / "features" / feature_id
    branch_name = get_branch_name(feature_id)
    
    # Read all feature documents from the worktree
    spec = read_file_safe(feature_path / "spec.md")
    design = read_file_safe(feature_path / "design.md")
    tasks = read_file_safe(feature_path / "tasks.md")
    status = read_file_safe(feature_path / "status.md")
    
    prompt = f'''
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     ISOLATED FEATURE DEVELOPMENT CONTEXT                       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  Feature: {feature_id}
║  Role: {role["name"]}
║  Branch: {branch_name}
║  Worktree: {worktree_path}
║  Started: {datetime.now().strftime("%Y-%m-%d %H:%M")}
╚═══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════════════
⚠️  IMPORTANT: YOU ARE IN AN ISOLATED WORKTREE
═══════════════════════════════════════════════════════════════════════════════

This is a separate copy of the repository. You can work freely without 
affecting other developers or features.

WORKTREE PATH: {worktree_path}
BRANCH: {branch_name}

Your changes will be merged to main via Pull Request after completion.

═══════════════════════════════════════════════════════════════════════════════
YOUR ROLE AND RESPONSIBILITIES
═══════════════════════════════════════════════════════════════════════════════

You are the **{role["name"]}** for feature {feature_id}.

YOUR FOCUS:
{role["focus"]}

TASKS SECTION TO WORK ON:
{role["tasks_section"]} section in tasks.md

FILES YOU SHOULD MODIFY:
{role["files_pattern"]}

DO NOT TOUCH:
{role["do_not_touch"]}

═══════════════════════════════════════════════════════════════════════════════
GIT WORKFLOW (git-automator integration)
═══════════════════════════════════════════════════════════════════════════════

You are on branch: {branch_name}

COMMIT WORKFLOW (per task):
1. Stage: git add [files for this task only]
2. Commit: git commit -m "{feature_id}: [Action] [Component] - [description]"
3. Continue to next task...

COMMIT MESSAGE FORMAT:
- Keep under 72 characters
- Start with feature ID: "{feature_id}: "
- Use present tense ("Add" not "Added")
- Be specific: "Add User model" not "Update files"

PUSH SCHEDULE:
- After every 3 tasks OR every 30 minutes
- Command: git push origin {branch_name}

WHEN ALL TASKS COMPLETE:
1. Final push: git push -u origin {branch_name}
2. Create PR: gh pr create --title "{feature_id}: [Feature Name]" --base main
3. Or manual: https://github.com/[user]/[repo]/compare/{branch_name}

IF CONFLICTS OCCUR:
1. Run: git status (see conflicting files)
2. Read each conflicting file
3. Ask user which version to keep
4. Resolve and: git add [file] && git rebase --continue

DO NOT:
- Commit unrelated files
- Use generic messages like "update" or "fix"
- Push to main directly
- Merge from main without asking

═══════════════════════════════════════════════════════════════════════════════
DOCUMENTATION VIVA - UPDATE IN REAL TIME
═══════════════════════════════════════════════════════════════════════════════

1. BEFORE starting each task:
   - Update tasks.md: Change "- [ ] Task" to "- [🟡] Task"

2. AFTER completing each task:
   - Update tasks.md: Change "- [🟡] Task" to "- [x] Task"
   - Commit: git add . && git commit -m "{feature_id}: Complete Task N"

3. EVERY 30 MINUTES or 3 TASKS:
   - Update status.md with progress
   - git push origin {branch_name}

4. IF YOU HIT A BLOCKER:
   - Update tasks.md: Change to "- [🔴] Task (blocked: reason)"
   - Update status.md Blockers section
   - Continue with other tasks if possible

═══════════════════════════════════════════════════════════════════════════════
FEATURE SPECIFICATION (spec.md)
═══════════════════════════════════════════════════════════════════════════════

{spec}

═══════════════════════════════════════════════════════════════════════════════
TECHNICAL DESIGN (design.md)
═══════════════════════════════════════════════════════════════════════════════

{design}

═══════════════════════════════════════════════════════════════════════════════
TASKS - WORK ON "{role["tasks_section"]}" SECTION (tasks.md)
═══════════════════════════════════════════════════════════════════════════════

{tasks}

═══════════════════════════════════════════════════════════════════════════════
CURRENT STATUS (status.md)
═══════════════════════════════════════════════════════════════════════════════

{status}

═══════════════════════════════════════════════════════════════════════════════
YOUR FIRST ACTIONS
═══════════════════════════════════════════════════════════════════════════════

1. Verify you are in the correct worktree:
   pwd  # Should show: {worktree_path}
   
2. Verify you are on the correct branch:
   git branch --show-current  # Should show: {branch_name}

3. Find the first uncompleted task in YOUR SECTION ({role["tasks_section"]})

4. Mark it as in-progress in tasks.md

5. Start implementing

BEGIN WORKING NOW. Ask questions only if something is unclear or blocking.
'''
    
    return prompt


# =============================================================================
# TERMINAL LAUNCHING
# =============================================================================

def launch_terminal_windows(worktree_path: Path, feature_id: str, role_id: str, context_prompt: str):
    """Launch a new terminal in the worktree directory on Windows."""
    
    # Save context to file in the worktree
    context_dir = worktree_path / ".claude" / "contexts"
    context_dir.mkdir(parents=True, exist_ok=True)
    context_file = context_dir / f"CONTEXT_{role_id.upper()}.md"
    context_file.write_text(context_prompt, encoding='utf-8')
    
    # Claude command
    claude_cmd = 'claude --dangerously-skip-permissions'
    
    # Full command: cd to worktree, then run claude
    full_command = f'cd /d "{worktree_path}" && {claude_cmd}'
    
    # Window title
    window_title = f'{feature_id} - {role_id}'
    
    try:
        subprocess.Popen(
            ['cmd', '/c', 'start', window_title, 'cmd', '/k', full_command],
            shell=True
        )
        return True, str(context_file)
    except Exception as e:
        return False, str(e)


# =============================================================================
# CLI COMMANDS
# =============================================================================

def list_roles():
    """Print available roles."""
    print("\n🎭 Available Roles:\n")
    print("-" * 70)
    for role_id, role in ROLES.items():
        print(f"  {role_id:12} - {role['name']}")
        print(f"               Focus: {role['focus'][:50]}...")
        print()
    print("-" * 70)
    print("\nUsage: python fork_feature.py <FEAT-ID> <role>")
    print("Example: python fork_feature.py FEAT-001-auth backend")
    print("Example: python fork_feature.py FEAT-001-auth full")


def show_worktrees():
    """Show all active worktrees."""
    print("\n📁 Active Worktrees:\n")
    print("-" * 70)
    
    worktrees = list_worktrees()
    for wt in worktrees:
        path = wt.get("path", "unknown")
        branch = wt.get("branch", "unknown").replace("refs/heads/", "")
        print(f"  {path}")
        print(f"    Branch: {branch}")
        print()
    
    print("-" * 70)
    print(f"Total: {len(worktrees)} worktrees")


def cleanup_worktree(feature_id: str):
    """Remove all worktrees for a feature."""
    print(f"\n🧹 Cleaning up worktrees for {feature_id}...\n")
    
    repo_root = get_repo_root()
    repo_name = repo_root.name
    parent = repo_root.parent
    
    removed = 0
    for role in ROLES.keys():
        worktree_name = f"{repo_name}-{feature_id}-{role}"
        worktree_path = parent / worktree_name
        
        if worktree_path.exists():
            print(f"  Removing {worktree_path}...")
            success, msg = remove_worktree(worktree_path)
            if success:
                print(f"    ✅ Removed")
                removed += 1
            else:
                print(f"    ❌ Failed: {msg}")
    
    print(f"\n✅ Removed {removed} worktrees")


def fork_feature(feature_id: str, role_id: str):
    """Main function to fork a feature with worktree isolation."""
    
    # Validate role
    if role_id not in ROLES:
        print(f"❌ Unknown role: {role_id}")
        list_roles()
        return False
    
    # Validate feature exists
    repo_root = get_repo_root()
    feature_path = repo_root / "docs" / "features" / feature_id
    if not feature_path.exists():
        print(f"❌ Feature not found: {feature_path}")
        print(f"   Create it first with: /new-feature {feature_id}")
        return False
    
    role = ROLES[role_id]
    print(f"\n🚀 Forking {feature_id} as {role['name']}...")
    print(f"   Using git worktree for isolation\n")
    
    # Create worktree
    success, worktree_path, message = create_worktree(feature_id, role_id)
    if not success:
        print(f"❌ {message}")
        return False
    
    print(f"✅ {message}")
    
    # Build context
    context = build_context_prompt(feature_id, role_id, worktree_path)
    
    # Launch terminal
    success, context_file = launch_terminal_windows(worktree_path, feature_id, role_id, context)
    
    if success:
        branch_name = get_branch_name(feature_id)
        print(f"\n{'='*60}")
        print(f"✅ FORK CREATED SUCCESSFULLY")
        print(f"{'='*60}")
        print(f"\n📁 Worktree: {worktree_path}")
        print(f"🌿 Branch: {branch_name}")
        print(f"📄 Context: {context_file}")
        print(f"\n📋 In the new terminal, paste this to start:")
        print(f"{'─'*60}")
        print(f'"Read .claude/contexts/CONTEXT_{role_id.upper()}.md and follow the instructions"')
        print(f"{'─'*60}")
        print(f"\n⚠️  When done:")
        print(f"   1. git push -u origin {branch_name}")
        print(f"   2. Create PR to main")
        print(f"   3. After merge: python fork_feature.py --cleanup {feature_id}")
        return True
    else:
        print(f"\n❌ Error launching terminal: {context_file}")
        return False


# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("""
Fork Feature - Isolated Parallel Development with Git Worktrees

Usage:
    python fork_feature.py <FEAT-ID> <role>      Create isolated fork
    python fork_feature.py --list-roles          Show available roles
    python fork_feature.py --list-worktrees      Show active worktrees
    python fork_feature.py --cleanup <FEAT-ID>   Remove feature worktrees

Examples:
    python fork_feature.py FEAT-001-auth full
    python fork_feature.py FEAT-001-auth backend
    python fork_feature.py FEAT-002-dashboard full
    python fork_feature.py --cleanup FEAT-001-auth

Worktree Structure:
    proyecto/                          <- Main repo (you are here)
    proyecto-FEAT-001-auth-full/       <- Isolated worktree for feature
    proyecto-FEAT-002-dashboard-full/  <- Another isolated worktree
        """)
        sys.exit(1)
    
    # Handle flags
    if sys.argv[1] == "--list-roles":
        list_roles()
        sys.exit(0)
    
    if sys.argv[1] == "--list-worktrees":
        show_worktrees()
        sys.exit(0)
    
    if sys.argv[1] == "--cleanup":
        if len(sys.argv) < 3:
            print("❌ Specify feature ID: --cleanup FEAT-XXX")
            sys.exit(1)
        cleanup_worktree(sys.argv[2])
        sys.exit(0)
    
    # Main fork command
    if len(sys.argv) < 3:
        print("❌ Missing role. Usage: python fork_feature.py <FEAT-ID> <role>")
        print("   Use --list-roles to see available roles")
        sys.exit(1)
    
    feature_id = sys.argv[1]
    role_id = sys.argv[2].lower()
    
    success = fork_feature(feature_id, role_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
