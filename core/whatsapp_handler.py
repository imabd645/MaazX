"""
Core logic for the WhatsApp AI Agent.
Handles incoming messages, formats conversation history, queries the AI, and sends replies back to the bridge.
"""

import json
import requests
import database
import openrouter_client
from core.deepseek_client import chat_completion_with_tools

def handle_incoming_message(msg_data: dict):
    """
    Process an incoming WhatsApp message payload from the Node.js bridge.
    msg_data expects: 
    { "id": str, "from": str, "author": str, "body": str, "timestamp": int, "hasMedia": bool }
    """
    sender = msg_data.get("from")
    body = msg_data.get("body", "").strip()

    if not sender or not body:
        return

    # 1. Save incoming message to SQLite
    database.save_wa_message(sender, "user", body)

    # 2. Retrieve Contact Rules and History
    contact = database.get_wa_contact(sender)
    
    # Optional: whitelist mode - if we only want to reply to known contacts, uncomment:
    # if not contact:
    #     print(f"Ignoring unknown sender: {sender}")
    #     return
    
    contact_name = contact["name"] if contact and contact["name"] else "Unknown Contact"
    rules = contact["rules"] if contact and contact["rules"] else "Be helpful and conversational."

    # Get the last 20 messages for context
    history = database.get_wa_history(sender, limit=20)

    # 4. Generate AI Reply
    settings = database.load_settings()
    model_name = settings.get("model_name", "gemini-2.5-flash")
    owner_name = settings.get("wa_owner_name", "User")
    
    # Detect if sender is an admin
    from config import WHATSAPP_ADMIN_NUMBERS

    # Load settings to check for dynamic admin numbers
    admin_str = settings.get("wa_admin_numbers", "")
    # Parse comma-separated admin numbers
    dynamic_admins = [n.strip() for n in admin_str.split(",") if n.strip()]
    
    # Check if sender is in the hardcoded config OR the dynamic list
    is_admin = sender in WHATSAPP_ADMIN_NUMBERS or sender in dynamic_admins
    
    # Run Intent Classifier
    from core.intent_classifier import classify_intent
    intent = classify_intent(body)
    
    print(f"\n[WA Debug] Sender: {sender} | Admin: {is_admin} | Intent: {intent}")
    print(f"[WA Debug] User Message: {body}")

    # 3. Build the System Prompt
    if is_admin:
        system_prompt = f"""
        [ADMIN PRIVILEGES ENABLED]
        You are the {owner_name}'s AI Command Core. You are speaking to the ADMIN ({sender}).
        
        IDENTIFIED INTENT: {intent}
        WORKING DIRECTORY: {database.load_settings().get('cwd', 'Default')}
        
        POWERS:
        - You MUST use tools to fulfill requests.
        - To message someone else, use the 'send_whatsapp' tool.
        - To save a contact or update rules, use 'save_whatsapp_contact'.
        - You can also read/edit files, run shell commands, and schedule tasks.
        
        INSTRUCTIONS:
        1. If the admin asks to send a message, call 'send_whatsapp' immediately.
        2. If the admin asks to schedule something, use 'schedule_action'.
        3. Do NOT greet the user or be conversational if an action is requested. Just run the tool.
        4. Confirm actions briefly AFTER the tool has returned a result.
        5. CRITICAL: Do NOT use markdown formatting (no **, no *, no _). Use plain text or simple caps for headers.
        """
        permitted_tools = None # Admin gets everything
    else:
        system_prompt = f"""
        [USER MODE]
        You are an AI assistant managing WhatsApp for {owner_name}.
        You are talking to: {contact_name} ({sender}).
        Rules: {rules}
        
        POWERS:
        - You have access to Web Search tools to answer questions.
        
        INSTRUCTIONS:
        - Be concise and natural.
        - Use 'search_web' and 'read_webpage' if the user asks for information you don't have.
        - CRITICAL: Do NOT use markdown formatting (no **, no *, no _).
        """
        permitted_tools = ["search_web", "read_webpage"]
        # Force intent to task if they ask a question that needs search? 
        # Actually, allow_tools will be True below.

    reply_text = "I'm sorry, I encountered an error processing your message."

    try:
        # Build message history for DeepSeek
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # DEBUG: See exactly what we send to DeepSeek
        print(f"[WA Debug] Full Message Payload: {json.dumps(messages, indent=2)}")
        
        # DeepSeek Native Model execution
        result = chat_completion_with_tools(
            messages=messages,
            model_name=model_name,
            allow_tools=True, # EVERYONE GETS TOOLS NOW
            permitted_tools=permitted_tools
        )
        reply_text = result["reply"]
        
        if is_admin:
            print(f"[WA Debug] Admin Reply: {reply_text[:100]}...")
            if result.get("executed_tools"):
                print(f"[WA Debug] Tools Executed: {result['executed_tools']}")

    except Exception as e:
        print(f"AI Generation Error: {e}")
        reply_text = "Sorry, my brain went offline for a second! Try again."

    # 5. Save and Send Reply
    database.save_wa_message(sender, "assistant", reply_text)

    try:
        # Send back to Node.js Bridge
        res = requests.post(
            "http://127.0.0.1:3000/send",
            json={"to": sender, "message": reply_text},
            timeout=10
        )
        res.raise_for_status()
        print(f"Successfully sent reply to {sender}")
    except Exception as e:
        print(f"Failed to send message to bridge: {e}")

