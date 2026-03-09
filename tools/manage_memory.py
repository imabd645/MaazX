"""
Agent tool to save, recall, and delete long-term memory facts.
"""

from core.tool_registry import register_tool
import database as db

@register_tool
def remember_fact(key: str, value: str) -> str:
    """
    Saves a persistent memory or preference about the user into the SQLite database.
    This will be injected into every future chat session automatically.

    Args:
        key: A short, descriptive identifier for this memory (e.g., 'preferred_framework', 'user_name').
        value: The value or context of the memory to save.
    """
    db.save_memory(key, value)
    return f"Memory saved successfully! I will remember that '{key}' is: {value}"


@register_tool
def forget_fact(key: str) -> str:
    """
    Deletes a specific memory from the database.

    Args:
        key: The exact key of the memory to delete.
    """
    deleted = db.delete_memory(key)
    if deleted:
        return f"Successfully forgot the memory associated with '{key}'."
    else:
        return f"No memory found with the key '{key}'."


@register_tool
def list_memories() -> str:
    """
    Lists all saved user memories and preferences from the database.
    Returns a formatted string of key-value pairs.
    """
    memories = db.get_memories()
    if not memories:
        return "You have no saved memories."
    
    output = "Here are your saved memories:\n"
    for k, v in memories.items():
        output += f"- {k}: {v}\n"
    return output
