"""
Tools for managing WhatsApp contacts and automated behaviors.
"""

from core.tool_registry import register_tool
import database

@register_tool
def save_whatsapp_contact(phone_number: str, name: str, rules: str = "", auto_reply: bool = True):
    """
    Save or update a WhatsApp contact's configuration, including behavior rules and auto-reply permissions.
    
    Args:
        phone_number (str): The WhatsApp ID (e.g., '923123456789@c.us')
        name (str): A friendly name for the contact.
        rules (str): Specific instructions for how the AI should behave with this contact.
        auto_reply (bool): Whether the agent is allowed to automatically reply to this contact.
    """
    try:
        database.save_wa_contact(phone_number, name, summary="", rules=rules, auto_reply=int(auto_reply))
        status = "ENABLED" if auto_reply else "DISABLED"
        return f"Successfully saved contact {name} ({phone_number}). Auto-Reply: {status}."
    except Exception as e:
        return f"Error saving contact: {e}"

@register_tool
def wa_toggle_auto_reply(phone_number: str, enable: bool):
    """
    Enable or disable automatic AI replies for a specific WhatsApp contact.
    
    Args:
        phone_number (str): The WhatsApp ID (e.g., '923123456789@c.us').
        enable (bool): True to enable auto-reply, False to disable.
    """
    try:
        contact = database.get_wa_contact(phone_number)
        if not contact:
            return f"Error: Contact {phone_number} not found in database. Please save them first."
        
        database.save_wa_contact(
            phone_number, 
            contact["name"], 
            contact["summary"], 
            contact["rules"], 
            auto_reply=int(enable)
        )
        status = "ENABLED" if enable else "DISABLED"
        return f"Success! Auto-reply is now {status} for {contact['name']} ({phone_number})."
    except Exception as e:
        return f"Error toggling auto-reply: {e}"

@register_tool
def wa_set_global_auto_reply(enable: bool):
    """
    Set the default auto-reply behavior for unknown contacts or those without specific rules.
    
    Args:
        enable (bool): True to allow replies to everyone by default, False to be silent unless whitelisted.
    """
    try:
        settings = database.load_settings()
        settings["wa_default_auto_reply"] = bool(enable)
        database.save_settings(settings)
        status = "ALLOW ALL" if enable else "RESTRICTED (Wait for whitelist)"
        return f"Success! Global WhatsApp auto-reply policy set to: {status}."
    except Exception as e:
        return f"Error setting global policy: {e}"

@register_tool
def delete_whatsapp_contact(phone_number: str):
    """
    Delete a WhatsApp contact and its rules from the database.
    
    Args:
        phone_number (str): The WhatsApp ID to delete.
    """
    try:
        database.delete_wa_contact(phone_number)
        return f"Successfully deleted contact {phone_number}"
    except Exception as e:
        return f"Error deleting contact: {e}"
@register_tool
def search_saved_contacts(query: str):
    """
    Search for a WhatsApp contact ONLY in the local database.
    This does NOT search the live WhatsApp account. Use 'whatsapp_search_contacts' for that.
    
    Args:
        query (str): The name or partial name to search for in the database.
    """
    try:
        contacts = database.get_all_wa_contacts()
        # Find matches by name
        results = [c for c in contacts if query.lower() in (c.get('name') or '').lower()]
        if not results:
            return f"No contacts found in local database matching '{query}'"
        return f"Found contacts in database: {results}"
    except Exception as e:
        return f"Error searching database contacts: {e}"
@register_tool
def clear_whatsapp_history(phone_number: str = None):
    """
    Clear the chat history for a specific contact or for everyone (if no phone_number provided).
    
    Args:
        phone_number (str): The WhatsApp ID to clear (e.g., '923123456789@c.us').
    """
    try:
        database.clear_wa_history(phone_number)
        return f"Successfully cleared history for {phone_number if phone_number else 'all contacts'}."
    except Exception as e:
        return f"Error clearing history: {e}"
@register_tool
def trim_whatsapp_history(count: int, phone_number: str = None):
    """
    Delete a specific number of recent messages from the chat history.
    Useful for 'undoing' a few messages or clearing context errors.
    
    Args:
        count (int): Number of most recent messages to delete.
        phone_number (str): The WhatsApp ID (e.g., '923123456789@c.us').
    """
    try:
        if not phone_number:
            return "Error: phone_number is required to identify which chat to trim."
            
        database.delete_wa_latest_messages(phone_number, count)
        return f"Successfully deleted the last {count} messages for {phone_number}."
    except Exception as e:
        return f"Error trimming history: {e}"

@register_tool
def wa_block_contact(phone_number: str):
    """
    Blocks a contact on WhatsApp. This prevents them from messaging the bot.
    
    Args:
        phone_number (str): The WhatsApp ID to block (e.g., '923350806140@c.us').
    """
    try:
        import requests
        res = requests.post("http://127.0.0.1:3000/block", json={"contactId": phone_number}, timeout=15)
        res.raise_for_status()
        return f"Successfully blocked contact {phone_number} on WhatsApp."
    except Exception as e:
        return f"Error blocking contact: {e}"

@register_tool
def wa_unblock_contact(phone_number: str):
    """
    Unblocks a contact on WhatsApp.
    
    Args:
        phone_number (str): The WhatsApp ID to unblock (e.g., '923350806140@c.us').
    """
    try:
        import requests
        res = requests.post("http://127.0.0.1:3000/unblock", json={"contactId": phone_number}, timeout=15)
        res.raise_for_status()
        return f"Successfully unblocked contact {phone_number} on WhatsApp."
    except Exception as e:
        return f"Error unblocking contact: {e}"
