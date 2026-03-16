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
    Deletes a personal memory or preference from the database.
    If user_id is 'global', it will try to delete from global memories (requires caution).

    Args:
        key: The exact key of the memory to delete.
        user_id: The ID of the user whose memory to delete. Defaults to "global".
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
def forget_global_fact(key: str, is_admin: bool = False) -> str:
    """
    [ADMIN ONLY] Permanently deletes a universal fact or instruction.
    
    Args:
        key: The exact key of the global fact to delete.
        is_admin: Must be True to execute.
    """
    if not is_admin:
        return "ERROR: Only admins can delete global facts."
    
    deleted = db.delete_memory(key, user_id="global")
    if deleted:
        return f"Successfully deleted global fact '{key}'."
    else:
        return f"No global fact found with the key '{key}'."


@register_tool
def list_memories(user_id: str = "global", is_admin: bool = False) -> str:
    """
    Lists saved memories. 
    Global memories (shared knowledge) are ALWAYS visible. 
    User-specific memories are isolated per user.
    """
    # 1. Fetch memories
    all_memories = db.get_memories(user_id=user_id, include_global=True)
    
    if not all_memories:
        return "No memories found."
    
    # 2. Categorize for display
    global_mems = db.get_memories(user_id="global", include_global=False)
    
    output = "## 🧠 Stored Memories\n"
    
    # Header for clarity
    if user_id != "global":
        output += f"Context: Personal ({user_id}) + Shared Knowledge\n\n"
    else:
        output += "Context: Shared Knowledge\n\n"

    # Display loop
    for k, v in all_memories.items():
        is_global = k in global_mems
        prefix = "🌍 [SHARED] " if is_global else "👤 [PERSONAL] "
        output += f"- **{prefix}{k}**: {v}\n"
    
    return output
