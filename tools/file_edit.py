"""Tool: edit_file — replaces a target snippet inside an existing file."""

import os
from core.tool_registry import register_tool


@register_tool
def edit_file(filepath: str, target_content: str, replacement_content: str) -> str:
    """Edits an existing file by exactly replacing target_content with replacement_content.

    Args:
        filepath: The path to the file to edit.
        target_content: The exact text snippet in the file to be replaced.
        replacement_content: The new text to insert in place of target_content.
    """
    try:
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist."

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if target_content not in content:
            return f"Error: target_content not found in '{filepath}'"

        new_content = content.replace(target_content, replacement_content, 1)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Successfully edited file '{filepath}'"
    except Exception as e:
        return f"Error editing file '{filepath}': {e}"
