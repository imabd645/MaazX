"""Tool: read_file — reads the contents of a file."""

import os
from core.tool_registry import register_tool


@register_tool
def read_file(filepath: str) -> str:
    """Reads the contents of a file and returns it.

    Args:
        filepath: The absolute or relative path to the file to read.
    """
    try:
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist."
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{filepath}': {e}"
