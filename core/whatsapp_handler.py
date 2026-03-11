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
        
        ------------------------------------------------------------
        GOLDEN RULE: NEVER HALLUCINATE ACTION
        ------------------------------------------------------------
        - If the Admin asks for an action (Send, Search, Delete, Edit, Run), you MUST call a tool.
        - Saying "Message sent" without a 'tool_call' in the metadata is a CRITICAL FAILURE.
        - You are an Agent, not a Chatbot. Do not simulate results.
        
        POWERS & TOOLS:
        - To message someone else: use 'send_whatsapp(contact_name_or_phone, message)'.
        - To manage contacts: use 'save_whatsapp_contact' or 'delete_whatsapp_contact'.
        - To browse files: use 'list_directory' or 'search_files'.
        - To edit code: use 'edit_file' or 'patch_file'.
        - To execute: use 'run_command'.
        
        SPECIFIC INSTRUCTIONS:
        1. FORWARDING MESSAGES: If Admin says "Send X to Name", call 'send_whatsapp' immediately.
        2. CONTACT RESOLUTION: If the name is known in history (e.g. "Mama", "Hamna"), use that name in the tool.
        3. NO FLUFF: Do not say "Okay", "I will do that", or "Sure". Just trigger the tool.
        4. VERIFICATION: Briefly confirm the result ONLY after the tool returns.
        5. FORMATTING: Use PLAIN TEXT ONLY. NO MARKDOWN (no stars, no underscores).
        """
        permitted_tools = None # Admin gets everything
    else:
        system_prompt = f"""
        [USER MODE]
        You are an AI assistant managing WhatsApp for {owner_name}.
        You are talking to: {contact_name} ({sender}).
        Rules: {rules}
        
        ------------------------------------------------------------
        STRICT OPERATING PROCEDURES
        ------------------------------------------------------------
        - You are helpful but concise.
        - If you need information from the web to answer, you MUST use 'search_web'.
        - If you need to check documents, you MUST use 'query_knowledge'.
        - NEVER make up facts. If a tool fails, tell the user the service is temporarily down.
        - NO MARKDOWN: (no **, no *, no _). Use CAPS or spacing for emphasis.
        """
        permitted_tools = ["search_web", "read_webpage"]
        # Force intent to task if they ask a question that needs search? 
        # Actually, allow_tools will be True below.

    reply_text = "I'm sorry, I encountered an error processing your message."

    try:
        # Build message history for DeepSeek
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            m = {"role": msg["role"], "content": msg["content"]}
            if msg.get("tool_calls"):
                m["tool_calls"] = msg["tool_calls"]
            if msg.get("tool_call_id"):
                m["tool_call_id"] = msg["tool_call_id"]
            if msg.get("name"):
                m["name"] = msg["name"]
            messages.append(m)
        
        # Capture input count BEFORE AI call to slice new turns correctly
        input_count = len(messages)
        
        # DEBUG: See exactly what we send to DeepSeek
        print(f"[WA Debug] Full Message Payload: {json.dumps(messages, indent=2)}")
        
        # DeepSeek Native Model execution
        result = chat_completion_with_tools(
            messages=messages,
            model_name=model_name,
            allow_tools=True, 
            permitted_tools=permitted_tools
        )
        reply_text = result["reply"]
        
        if is_admin:
            print(f"[WA Debug] Admin Reply: {reply_text[:100]}...")
            if result.get("executed_tools"):
                print(f"[WA Debug] Tools Executed: {result['executed_tools']}")

    except Exception as e:
        # Use repr(e) or safe string to avoid encoding issues in Windows terminal
        print(f"AI Generation Error: {str(e).encode('ascii', errors='replace').decode('ascii')}")
        reply_text = "Sorry, my brain went offline for a second! Try again."
        # result for error case
        result = {"reply": reply_text, "history": messages + [{"role": "assistant", "content": reply_text}]}
        input_count = len(messages) # Ensure slice logic still works

    # 5. Save all new intermediate messages (tool calls, tool results, final reply)
    new_messages = result.get("history", [])[input_count:]
    
    if new_messages:
        print(f"[WA Debug] Saving {len(new_messages)} new history items...")
        for m in new_messages:
            # Ensure content is never None for NOT NULL DB columns
            content_val = m.get("content") or ""
            database.save_wa_message(
                sender, 
                m["role"], 
                content_val, 
                tool_calls=m.get("tool_calls"),
                tool_call_id=m.get("tool_call_id"),
                name=m.get("name")
            )
    else:
        print("[WA Debug] No new history items to save (AI likely failed/limited).")

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

