"""Tool: list_directory — lists all files and folders in a directory recursively."""

import os
from core.tool_registry import register_tool


@register_tool
def list_directory(directory_path: str, max_depth: int = 3) -> str:
    """Lists all files and subdirectories in the given directory, with tree-like output.

    Args:
        directory_path: The absolute path to the directory to list.
        max_depth: How many levels deep to recurse (default 3).
    """
    try:
        if not os.path.isdir(directory_path):
            return f"Error: '{directory_path}' is not a valid directory."

        lines = []
        base_depth = directory_path.rstrip(os.sep).count(os.sep)

        for root, dirs, files in os.walk(directory_path):
            current_depth = root.rstrip(os.sep).count(os.sep) - base_depth
            if current_depth >= max_depth:
                dirs.clear()
                continue

            indent = "  " * current_depth
            folder_name = os.path.basename(root) or root
            lines.append(f"{indent}📁 {folder_name}/")

            file_indent = "  " * (current_depth + 1)
            for f in sorted(files):
                size = os.path.getsize(os.path.join(root, f))
                lines.append(f"{file_indent}📄 {f}  ({size} bytes)")

            # Sort dirs for consistent output and skip hidden/venv dirs
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.git', 'venv', '.venv'))

        return "\n".join(lines) if lines else "Directory is empty."
    except Exception as e:
        return f"Error listing directory '{directory_path}': {e}"
