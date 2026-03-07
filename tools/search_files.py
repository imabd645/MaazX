"""Tool: search_files — find files by name or glob pattern."""

import os
import fnmatch
from core.tool_registry import register_tool


@register_tool
def search_files(directory_path: str, pattern: str) -> str:
    """Searches for files whose names match a glob pattern within a directory tree.

    Args:
        directory_path: The root directory to search in.
        pattern: A glob pattern to match file names (e.g. '*.py', 'test_*', '*.js').
    """
    try:
        if not os.path.isdir(directory_path):
            return f"Error: '{directory_path}' is not a valid directory."

        matches = []
        skip_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', '.idea', '.vs'}

        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for filename in files:
                if fnmatch.fnmatch(filename, pattern):
                    full_path = os.path.join(root, filename)
                    matches.append(full_path)
                    if len(matches) >= 50:
                        matches.append("... (results capped at 50)")
                        return "\n".join(matches)

        if not matches:
            return f"No files matching '{pattern}' found in '{directory_path}'."
        return "\n".join(matches)
    except Exception as e:
        return f"Error searching files: {e}"
