"""
Git integration for automatic backups.
Used to snapshot the working directory before and after agent edits so the user can undo them.
"""

import os
import subprocess

def _find_git_root(cwd: str) -> str:
    """Find the root of the git repository starting from cwd, or return None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return None

def _is_dirty(git_root: str) -> bool:
    """Check if the working tree has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_root, capture_output=True, text=True, check=True
        )
        return bool(result.stdout.strip())
    except Exception:
        return False

def backup_before_edit(filepath: str):
    """
    Called before the agent edits a file.
    If the working tree has unsaved changes made by the user, we commit them
    as "Auto backup before agent edit" so they aren't lost if the user undoes the agent's action.
    """
    if not os.path.exists(filepath):
        # We can still backup relative to the parent dir if it's a new file
        git_root = _find_git_root(os.path.dirname(filepath))
    else:
        git_root = _find_git_root(os.path.dirname(filepath))
        
    if not git_root:
        return

    if _is_dirty(git_root):
        try:
            subprocess.run(["git", "add", "."], cwd=git_root, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Auto backup before agent edit"], cwd=git_root, capture_output=True)
        except Exception as e:
            print(f"Git backup error: {e}")

def commit_after_edit(filepath: str, tool_name: str):
    """
    Called after the agent successfully edits a file.
    Creates a new commit capturing specifically the agent's changes.
    """
    if not os.path.exists(filepath):
        git_root = _find_git_root(os.path.dirname(filepath))
    else:
        git_root = _find_git_root(os.path.dirname(filepath))
        
    if not git_root:
        return

    try:
        # We only add the specifically edited file, just to be safe, but adding all is okay too if the
        # agent created a new file and we want to track it.
        subprocess.run(["git", "add", "."], cwd=git_root, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Agent Tool Action: {tool_name}"], cwd=git_root, capture_output=True)
    except Exception as e:
        print(f"Git commit error: {e}")

def undo_last_agent_action(cwd: str) -> dict:
    """
    Reverts the last commit IF it was an agent action or auto-backup.
    Returns a dict with {"success": bool, "message": str}
    """
    git_root = _find_git_root(cwd)
    if not git_root:
        return {"success": False, "message": "Not a git repository."}

    try:
        # Check last commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            cwd=git_root, capture_output=True, text=True, check=True
        )
        msg = result.stdout.strip()

        if "Agent Tool Action:" in msg:
            # We revert the Agent's change (this destroys the agent's commit and working tree edits)
            subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=git_root, capture_output=True, check=True)
            
            # Now let's check if the commit before that was an "Auto backup before agent edit".
            # If so, we might want to optionally keep that one, or uncommit it so the working tree is dirty again.
            # Usually, uncommitting it is best so the user gets their unstaged changes back exactly as they were.
            res2 = subprocess.run(
                ["git", "log", "-1", "--pretty=%B"],
                cwd=git_root, capture_output=True, text=True
            )
            msg2 = res2.stdout.strip()
            
            if "Auto backup before agent edit" in msg2:
                # Do a soft reset so the user's uncommitted changes go back to the working directory/staging area
                subprocess.run(["git", "reset", "--soft", "HEAD~1"], cwd=git_root, capture_output=True)
                # and maybe git reset to unstage them to be exactly as they probably were
                subprocess.run(["git", "reset"], cwd=git_root, capture_output=True)
                return {"success": True, "message": "Agent edit reversed. Your previous unsaved changes have been restored to your working tree!"}

            return {"success": True, "message": f"Successfully reversed: {msg}"}
        else:
            return {"success": False, "message": "Last commit was not an Agent action. Cannot undo safely."}
    except Exception as e:
        return {"success": False, "message": f"Undo failed: {str(e)}"}
