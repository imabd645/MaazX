"""
Tool for managing Git operations and GitHub integration.
"""

import subprocess
import os
from core.tool_registry import register_tool

def _run_git(args, cwd=None):
    """Helper to run git commands."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()
    except Exception as e:
        return f"Exception running git: {str(e)}"

@register_tool
def git_sync(message: str = None) -> str:
    """
    Stages all changes, commits them, and pushes to the current branch.
    
    Args:
        message: Optional. The commit message. If not provided, a generic AI message is used.
    """
    cwd = os.getcwd()
    
    # 1. Add all
    add_res = _run_git(["add", "."], cwd)
    if "Error" in add_res:
        return f"Failed to stage changes: {add_res}"
        
    # 2. Check if there are changes to commit
    status = _run_git(["status", "--porcelain"], cwd)
    if not status:
        return "No changes to commit (everything is up to date)."
        
    # 3. Commit
    commit_msg = message or "AI Agent: Automated sync"
    commit_res = _run_git(["commit", "-m", commit_msg], cwd)
    if "Error" in commit_res:
        return f"Failed to commit: {commit_res}"
        
    # 4. Push
    push_res = _run_git(["push"], cwd)
    if "Error" in push_res:
        return f"Commit successful, but push failed: {push_res}"
        
    return f"Successfully synced changes to git with message: '{commit_msg}'\n{push_res}"

@register_tool
def get_git_diff() -> str:
    """
    Returns a summary of the current uncommitted changes (git diff).
    """
    diff = _run_git(["diff", "HEAD"])
    if not diff:
        return "No uncommitted changes."
    
    # Return first 2000 characters to avoid overwhelming WhatsApp
    if len(diff) > 2000:
        return diff[:2000] + "\n\n...[truncated]..."
    return diff

@register_tool
def create_github_issue(title: str, body: str) -> str:
    """
    Creates a new issue on the current GitHub repository using the GitHub CLI (gh).
    Assumes the user is already logged into the GitHub CLI.
    
    Args:
        title: The title of the issue.
        body: The detailed description of the issue.
    """
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            if "not logged in" in result.stderr or "gh: command not found" in result.stderr:
                return "Error: GitHub CLI (gh) is not installed or not logged in. Please run 'gh auth login' on the server."
            return f"Error: {result.stderr.strip()}"
        return f"Successfully created GitHub issue: {result.stdout.strip()}"
    except Exception as e:
        return f"Exception running gh: {str(e)}"
