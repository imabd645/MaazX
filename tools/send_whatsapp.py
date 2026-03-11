"""Tool: send_whatsapp — proactively send a WhatsApp message to a contact."""

import requests
import database as db
from core.tool_registry import register_tool

@register_tool
def send_whatsapp(contact_name_or_phone: str, message: str) -> str:
    """Sends a WhatsApp message proactively to a contact.
    The contact must already exist in the database or you must provide their full WhatsApp ID (e.g. 1234567890@c.us).
    
    Args:
        contact_name_or_phone: The name of the contact as saved in the system, or their direct phone ID.
        message: The final text message to send.
    """
    contacts = db.get_all_wa_contacts()
    
    # 1. Try to find by exact phone or exact name match (case-insensitive)
    matched_phone = contact_name_or_phone
    matched_name = "Unknown"
    found = False
    
    for c in contacts:
        if c["phone_number"] == contact_name_or_phone or c.get("name", "").lower() == contact_name_or_phone.lower():
            matched_phone = c["phone_number"]
            matched_name = c.get("name", "Unknown Contact")
            found = True
            break
            
    # If not found but looks like a generic name, we might want to warn
    if not found and "@c.us" not in contact_name_or_phone and "@g.us" not in contact_name_or_phone:
        # Give a helpful error with available contacts
        available = ", ".join([f"{c.get('name', 'Unknown')} ({c['phone_number']})" for c in contacts])
        return f"Error: Could not find contact matching '{contact_name_or_phone}'. Available contacts: {available}"
        
    # 2. Skip saving to history here as the WhatsApp handler now saves the full turn history.
    
    # 3. Send to Node.js bridge
    try:
        from core.utils import strip_markdown
        plain_message = strip_markdown(message)
        
        res = requests.post(
            "http://127.0.0.1:3000/send",
            json={"to": matched_phone, "message": plain_message},
            timeout=15
        )
        res.raise_for_status()
        return f"Success! WhatsApp message sent to {matched_name} ({matched_phone})."
    except Exception as e:
        return f"Failed to send WhatsApp message to {matched_phone}: {e}"
