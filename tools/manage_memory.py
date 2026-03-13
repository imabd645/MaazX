"""
Agent tool to save, recall, and delete long-term memory facts.
"""

from core.tool_registry import register_tool
import database as db

@register_tool
def remember_fact(key: str, value: str, user_id: str = "global") -> str:
    """
    Saves a persistent memory or preference about the user into the SQLite database.
    This will be isolated to the current user.

    Args:
        key: A short, descriptive identifier for this memory.
        value: The value or context of the memory to save.
    """
    db.save_memory(key, value, user_id=user_id)
    return f"Memory saved successfully! I will remember that '{key}' is: {value}"


@register_tool
def forget_fact(key: str, user_id: str = "global") -> str:
    """
    Deletes a specific memory from the database.

    Args:
        key: The exact key of the memory to delete.
    """
    deleted = db.delete_memory(key, user_id=user_id)
    if deleted:
        return f"Successfully forgot the memory associated with '{key}'."
    else:
        return f"No memory found with the key '{key}'."


@register_tool
def set_global_instruction(key: str, value: str, is_admin: bool = False) -> str:
    """
    [ADMIN ONLY] Sets a universal fact or instruction that applies to ALL users.
    Example: 'creator', 'Abdullah Masood'.
    """
    if not is_admin:
        return "ERROR: Only admins can set global instructions."
    
    db.save_memory(key, value, user_id="global")
    return f"Global Instruction set: '{key}' is now universally set to: {value}"


@register_tool
def list_memories(user_id: str = "global", is_admin: bool = False) -> str:
    """
    Lists saved user memories. 
    Admins see global + personal. Users see ONLY personal.
    """
    # 1. Fetch personal + global
    all_memories = db.get_memories(user_id=user_id, include_global=True)
    
    # 2. Filter for visibility logic
    if not is_admin:
        # Hide global keys from listing for regular users
        global_keys = db.get_memories(user_id="global", include_global=False).keys()
        display_mems = {k: v for k, v in all_memories.items() if k not in global_keys}
    else:
        display_mems = all_memories

    if not display_mems:
        return "You have no saved memories."
    
    output = "Here are your saved memories:\n"
    for k, v in display_mems.items():
        prefix = "[GLOBAL] " if is_admin and k in db.get_memories(user_id="global", include_global=False) else ""
        output += f"- {prefix}{k}: {v}\n"
    return output
