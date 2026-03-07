"""Tool: search_in_files — grep-like content search across files."""

import os
from core.tool_registry import register_tool


@register_tool
def search_in_files(directory_path: str, query: str, file_pattern: str = "*") -> str:
    """Searches for a text string inside files within a directory, like grep.

    Args:
        directory_path: The root directory to search in.
        query: The text string to search for inside file contents.
        file_pattern: Optional glob pattern to filter which files to search (default '*' = all files).
    """
    import fnmatch

    try:
        if not os.path.isdir(directory_path):
            return f"Error: '{directory_path}' is not a valid directory."

        results = []
        skip_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.venv'}
        binary_exts = {'.exe', '.dll', '.so', '.bin', '.o', '.pyc', '.pyd',
                       '.png', '.jpg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz'}

        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for filename in files:
                if os.path.splitext(filename)[1].lower() in binary_exts:
                    continue
                if file_pattern != "*" and not fnmatch.fnmatch(filename, file_pattern):
                    continue

                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if query in line:
                                results.append(f"{filepath}:{line_num}: {line.rstrip()}")
                                if len(results) >= 50:
                                    results.append("... (results capped at 50)")
                                    return "\n".join(results)
                except (PermissionError, OSError):
                    continue

        if not results:
            return f"No matches for '{query}' found in '{directory_path}'."
        return "\n".join(results)
    except Exception as e:
        return f"Error during search: {e}"
