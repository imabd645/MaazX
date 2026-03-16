"""
GitHub Automation Tools for MaazX.
Provides repository creation, file pushing, and Pages enablement using GitHub REST API and Git CLI.
"""

import os
import subprocess
import requests
import json
import config
from core.tool_registry import register_tool

def _get_headers():
    if not config.GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN is missing in agent_secrets.env")
    return {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def _get_username():
    """Fetches the authenticated username from GitHub."""
    resp = requests.get("https://api.github.com/user", headers=_get_headers())
    resp.raise_for_status()
    return resp.json()["login"]

@register_tool
def github_create_repo(name: str, description: str = "", private: bool = False) -> str:
    """
    Creates a new repository on GitHub.
    
    Args:
        name: Name of the repository.
        description: Optional description.
        private: Whether the repo should be private. Defaults to False.
    """
    url = "https://api.github.com/user/repos"
    data = {
        "name": name,
        "description": description,
        "private": private,
        "auto_init": False
    }
    
    try:
        resp = requests.post(url, headers=_get_headers(), json=data)
        if resp.status_code == 201:
            repo_data = resp.json()
            return f"Successfully created repository: {repo_data['html_url']}"
        else:
            return f"Error creating repository: {resp.status_code} - {resp.text}"
    except Exception as e:
        return f"Exception creating repository: {str(e)}"

@register_tool
def github_init_and_push(target_dir: str, repo_url: str, branch: str = "main", message: str = "Initial commit") -> str:
    """
    Initialises a git repository in target_dir and pushes to the specified remote.
    
    Args:
        target_dir: Absolute path to the directory to push.
        repo_url: The GitHub repository URL (e.g. https://github.com/user/repo.git).
        branch: The branch name (usually 'main').
        message: Commit message.
    """
    if not os.path.isabs(target_dir):
        return "Error: target_dir must be an absolute path."
    
    if not os.path.exists(target_dir):
        return f"Error: Directory {target_dir} does not exist."

    def run_git(args):
        return subprocess.run(["git"] + args, cwd=target_dir, capture_output=True, text=True)

    try:
        # 1. Git Init
        if not os.path.exists(os.path.join(target_dir, ".git")):
            run_git(["init", "-b", branch])
        
        # 2. Add Remote (re-add if already exists)
        run_git(["remote", "remove", "origin"])
        
        # Inject token into URL for authenticated push
        if "https://" in repo_url:
            authenticated_url = repo_url.replace("https://", f"https://{config.GITHUB_TOKEN}@")
        else:
            authenticated_url = repo_url
            
        res = run_git(["remote", "add", "origin", authenticated_url])
        if res.returncode != 0: return f"Error adding remote: {res.stderr}"

        # 3. Add & Commit
        run_git(["add", "."])
        res = run_git(["commit", "-m", message])
        # Note: If no changes, commit might fail, but we proceed to push anyway

        # 4. Push
        res = run_git(["push", "-u", "origin", branch, "--force"])
        if res.returncode == 0:
            return f"Successfully pushed files to {repo_url} on branch {branch}"
        else:
            return f"Error pushing files: {res.stderr}"
            
    except Exception as e:
        return f"Exception during git push: {str(e)}"

@register_tool
def github_enable_pages(repo_name: str, branch: str = "main", path: str = "/") -> str:
    """
    Enables GitHub Pages for a repository and returns the live URL.
    
    Args:
        repo_name: Name of the repository (case-sensitive).
        branch: The source branch.
        path: The source path (e.g. '/' or '/docs').
    """
    try:
        username = _get_username()
        url = f"https://api.github.com/repos/{username}/{repo_name}/pages"
        data = {
            "source": {
                "branch": branch,
                "path": path
            }
        }
        
        # Verify if Pages is already enabled
        check_resp = requests.get(url, headers=_get_headers())
        if check_resp.status_code == 200:
            pages_data = check_resp.json()
            return f"GitHub Pages is already active: {pages_data['html_url']}"

        # Enable Pages
        resp = requests.post(url, headers=_get_headers(), json=data)
        if resp.status_code == 201:
            pages_data = resp.json()
            return f"Successfully enabled GitHub Pages! Live URL: {pages_data.get('html_url') or f'https://{username}.github.io/{repo_name}/'}"
        else:
            return f"Error enabling GitHub Pages: {resp.status_code} - {resp.text}"
            
    except Exception as e:
        return f"Exception enabling Pages: {str(e)}"

@register_tool
def github_delete_repo(repo_name: str, is_admin: bool = False) -> str:
    """
    [ADMIN ONLY] Deletes a repository on GitHub.
    
    Args:
        repo_name: Name of the repository to delete.
        is_admin: Must be True to execute.
    """
    if not is_admin:
        return "ERROR: Only admins can delete GitHub repositories."
        
    try:
        username = _get_username()
        url = f"https://api.github.com/repos/{username}/{repo_name}"
        
        resp = requests.delete(url, headers=_get_headers())
        if resp.status_code == 204:
            return f"Successfully deleted repository: {repo_name}"
        else:
            return f"Error deleting repository: {resp.status_code} - {resp.text}"
            
    except Exception as e:
        return f"Exception deleting repository: {str(e)}"
