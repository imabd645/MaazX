"""
Agent tool for Universal File Porter.
Allows the agent to send files from the local PC to WhatsApp.
"""

import os
import requests
from core.tool_registry import register_tool

@register_tool
def pc_send_file(filename: str, contact: str = None) -> str:
    """
    Finds a file on the local PC (Desktop, Downloads, or Documents) and sends it to WhatsApp.
    
    Args:
        filename: The name of the file to send (e.g., 'Project_Plan.pdf', 'invoice.jpg').
        contact: Optional. The WhatsApp phone number or ID. If not provided, it sends to the admin who requested it.
    """
    # 1. Common search locations
    home = os.path.expanduser("~")
    search_dirs = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Downloads"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Downloads", "WhatsApp_Inbox")
    ]
    
    target_path = None
    
    # If the user provided a full path, use it directly
    if os.path.isabs(filename) and os.path.exists(filename):
        target_path = filename
    else:
        # Search for the file in common directories
        for d in search_dirs:
            if not os.path.exists(d): continue
            potential_path = os.path.join(d, filename)
            if os.path.exists(potential_path):
                target_path = potential_path
                break
                
    if not target_path:
        return f"Error: Could not find file '{filename}' in common folders (Desktop, Downloads, Documents)."
        
    # 2. Forward to Bridge
    try:
        # If no contact provided, the core/handler will usually pass the sender ID
        # but in tool schema we just need to ensure the bridge gets a 'to'.
        # If 'contact' is None here, it's a tool-call context issue.
        if not contact:
            return f"Error: No recipient contact provided. Found file at {target_path}, but don't know where to send it."

        payload = {
            "to": contact,
            "filePath": target_path,
            "caption": f"Here is the file you requested: {os.path.basename(target_path)}"
        }
        
        resp = requests.post("http://localhost:3000/send_media", json=payload, timeout=20)
        if resp.status_code == 200:
            return f"Successfully sent '{os.path.basename(target_path)}' from {os.path.dirname(target_path)} to {contact}."
        else:
            return f"Failed to send file. Bridge returned: {resp.text}"
            
    except Exception as e:
        return f"Error during file transfer: {str(e)}"
