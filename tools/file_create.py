"""Tool: create_file — creates a new file with given content."""

import os
from core.tool_registry import register_tool


@register_tool
def create_file(filepath: str, content: str) -> str:
    """Creates a new file with the specified text content.

    Args:
        filepath: The path where the file should be created.
        content: The text content to write to the file.
    """
    try:
        os_dir = os.path.dirname(os.path.abspath(filepath))
        if os_dir:
            os.makedirs(os_dir, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully created file '{filepath}'"
    except Exception as e:
        return f"Error creating file '{filepath}': {e}"
