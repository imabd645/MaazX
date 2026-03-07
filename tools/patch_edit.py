"""
Advanced editing tool that allows multiple specific block replacements in a single pass.
This is similar to a structured unified diff, avoiding the fragility of strict line-based patch applying,
and avoiding the need to read/rewrite huge files blindly.
"""

import os
from core.tool_registry import register_tool
from core import git_backup

@register_tool
def patch_file(filepath: str, replacements: list) -> str:
    """
    Apply multiple exact-text replacements to a file. This is better than edit_file for large changes.

    Args:
        filepath: Absolute path to the file.
        replacements: A list of dicts. Each dict must have:
            - "target_content": The exact text snippet you want to find and replace.
            - "replacement_content": The text to insert in its place.

    Returns:
        A string indicating success or detailing errors.
    """
    if not os.path.exists(filepath):
        return f"Error: File '{filepath}' does not exist."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Validate all blocks first
        failures = []
        for i, block in enumerate(replacements):
            target = block.get("target_content", "")
            if not target:
                continue
            if content.count(target) != 1:
                if content.count(target) == 0:
                    failures.append(f"Block {i}: target text not found.")
                else:
                    failures.append(f"Block {i}: target text matches {content.count(target)} times. Must be unique.")

        if failures:
            return "Patch failed. " + " | ".join(failures)

        git_backup.backup_before_edit(filepath)

        # Apply all
        for block in replacements:
            target = block.get("target_content", "")
            new_text = block.get("replacement_content", "")
            if target:
                content = content.replace(target, new_text, 1)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        git_backup.commit_after_edit(filepath, "patch_edit")

        return f"Successfully applied {len(replacements)} patch blocks to '{filepath}'"
    except Exception as e:
        return f"Error patching file '{filepath}': {e}"
