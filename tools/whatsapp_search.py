"""
Tools for searching WhatsApp information: contacts and messages.
"""

import requests
import json
from typing import Optional, List, Dict, Any
from core.tool_registry import register_tool

BRIDGE_URL = "http://127.0.0.1:3000"

@register_tool
def whatsapp_search_contacts(query: str) -> str:
    """
    Searches for contacts on WhatsApp by name, pushname, or phone number.
    Use this to find people who are not in the local database.
    
    Args:
        query: The name or phone number fragment to search for.
    """
    try:
        res = requests.get(f"{BRIDGE_URL}/contacts/search", params={"query": query}, timeout=20)
        res.raise_for_status()
        data = res.json()
        
        if not data.get("success") or not data.get("results"):
            return f"No WhatsApp contacts found matching '{query}'."
            
        results = data["results"]
        output = [f"Found {len(results)} matching contacts:"]
        for c in results:
            contact_type = "[Group]" if c.get("isGroup") else "[Contact]"
            is_saved = "[SAVED]" if c.get("isMyContact") else "       "
            output.append(f"- {is_saved} {contact_type} {c['name']} ({c['id']})")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error searching WhatsApp contacts: {str(e)}"

@register_tool
def whatsapp_search_messages(query: str, limit: int = 20) -> str:
    """
    Searches through all WhatsApp chat history for messages containing a specific keyword or phrase.
    
    Args:
        query: The keyword or phrase to search for.
        limit: Max number of results to return (default 20).
    """
    try:
        res = requests.get(f"{BRIDGE_URL}/messages/search", params={"query": query, "limit": limit}, timeout=30)
        res.raise_for_status()
        data = res.json()
        
        if not data.get("success") or not data.get("results"):
            return f"No WhatsApp messages found containing '{query}'."
            
        results = data["results"]
        output = [f"Found {len(results)} messages matching '{query}':"]
        for m in results:
            direction = "TO  " if m.get("fromMe") else "FROM"
            timestamp = m.get("timestamp")
            import datetime
            dt = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
            
            output.append(f"[{dt}] {direction} {m['from'] if not m.get('fromMe') else m['to']}:")
            output.append(f"  > {m['body']}\n")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error searching WhatsApp messages: {str(e)}"
