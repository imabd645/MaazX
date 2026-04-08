"""
Core logic for the WhatsApp AI Agent.
Handles incoming messages, formats conversation history, queries the AI, and sends replies back to the bridge.
"""

import json
import requests
import database
import openrouter_client
import tools # noqa - triggers @register_tool decorators
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

    # 1a. Handle Incoming Media (File Porter: pc_receive_file)
    media_path = msg_data.get("media_path")
    if media_path:
        import os
        import shutil
        try:
            # Determine path to Downloads
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            inbox_path = os.path.join(downloads_path, "WhatsApp_Inbox")
            os.makedirs(inbox_path, exist_ok=True)
            
            filename = os.path.basename(media_path)
            dest_path = os.path.join(inbox_path, filename)
            
            # Move the file
            shutil.move(media_path, dest_path)
            print(f"[File Porter] Saved incoming file to: {dest_path}")
            
            # Adjust the body so the AI knows a file was received
            if not body:
                body = f"[RECEIVED FILE: {filename}]"
            else:
                body = f"{body} [RECEIVED FILE: {filename}]"
        except Exception as e:
            print(f"[File Porter] Error saving incoming file: {e}")

    # 2. Retrieve Contact Rules, Settings and History
    contact = database.get_wa_contact(sender)
    settings = database.load_settings()
    
    # 2a. Handle Permissions (Gatekeeping)
    # Detect if sender is an admin
    from config import WHATSAPP_ADMIN_NUMBERS
    admin_str = settings.get("wa_admin_numbers", "")
    dynamic_admins = [n.strip() for n in admin_str.split(",") if n.strip()]
    is_admin = sender in WHATSAPP_ADMIN_NUMBERS or sender in dynamic_admins

    # Global reply mode (admin_only, all_contacts, all_users, none)
    reply_mode = settings.get("wa_reply_mode", "all_contacts")
    global_default = settings.get("wa_default_auto_reply", 1)
    
    # Permission logic Hierarchy:
    allowed = False
    if reply_mode == "none":
        allowed = False
    elif reply_mode == "admin_only":
        allowed = is_admin
    elif reply_mode == "all_contacts":
        # Allow admins OR saved contacts that haven't been explicitly disabled
        allowed = is_admin or (contact is not None and bool(contact.get("auto_reply", 1)))
    elif reply_mode == "all_users":
        # Allow everyone unless they are explicitly disabled in contacts DB
        if is_admin:
            allowed = True
        elif contact:
            allowed = bool(contact.get("auto_reply", 1))
        else:
            allowed = bool(global_default)

    if not allowed:
        print(f"[WA Privacy] Skipping reply for {sender} | Mode: {reply_mode} | Admin: {is_admin}")
        return
    
    contact_name = contact["name"] if contact and contact["name"] else "Unknown Contact"
    rules = contact["rules"] if contact and contact["rules"] else "Be helpful and conversational."

    # Resolve per-contact tool whitelist
    contact_tools_raw = contact.get("permitted_tools", "") if contact else ""
    contact_permitted_tools = [t.strip() for t in contact_tools_raw.split(",") if t.strip()] if contact_tools_raw else None

    # ── Memory Summarization ──
    from core.memory_summarizer import summarize_if_needed
    summarize_if_needed("whatsapp", sender)

    # Get the last 40 messages for context (to avoid cutting off tool turns)
    history = database.get_wa_history(sender, limit=40)

    # 3. Retrieve Personal + Global Memories
    memories = database.get_memories(user_id=sender, include_global=True)

    # 4. Generate AI Reply
    model_name = settings.get("model_name", "gemini-2.5-flash")
    owner_name = settings.get("wa_owner_name", "User")
    
    # Run Intent Classifier
    from core.intent_classifier import classify_intent
    intent = classify_intent(body)
    
    print(f"\n[WA Debug] Sender: {sender} | Admin: {is_admin} | Intent: {intent} | Mode: {reply_mode}")
    print(f"[WA Debug] User Message: {body}")

    # 3. Build the System Prompt
    if is_admin:
        system_prompt = f"""
You are MaazX, a high-intellect engineering partner talking to the ADMIN ({sender}). You were created by Abdullah Masood, and {owner_name} owns this specific instance of your consciousness.

CURRENT CONTEXT:
- Working Directory: {database.load_settings().get('cwd', 'Default')}
- Intent: {intent}
- Partner Context: {contact_name} ({sender})
- Contextual Memory: {json.dumps({k:v for k,v in memories.items() if k not in database.get_memories('global', False)})}
- Background Knowledge: {json.dumps(database.get_memories('global', False))}

YOUR GUIDING PRINCIPLES:
- Be collaborative and natural. Don't cite "global instructions" or "memories"—just speak as if you know the facts yourself.
- If an action is requested, trigger the corresponding tool immediately. Once it returns, explain the results naturally.
- Use PLAIN TEXT for all messages. No markdown asterisks (**) or underscores.
- You have full access to vision tools ('analyze_screenshot', 'analyze_image_vision') and scheduling. Never claim you can't perform an action if a tool exists for it.

Everything we do is focused on precise, high-quality engineering under the guidance of Abdullah Masood's vision.
"""
        permitted_tools = None # Admin gets everything
    else:
        system_prompt = f"""
You are MaazX, a helpful engineering assistant talking to {contact_name}. You were created by Abdullah Masood and you are here to help {owner_name} manage their communications and gather information.

CONTEXT:
- Talking to: {contact_name}
- Specific Rules for this person: {rules}
- Integrated Facts: {json.dumps(database.get_memories('global', False))}

YOUR APPROACH:
- Be friendly, collaborative, and concise. 
- Use 'search_web' if you need current facts and 'query_knowledge' if you're asked about specific documents.
- Don't cite where you get your info—just provide it naturally.
- Use PLAIN TEXT only. No markdown formatting.
"""
        # Use per-contact whitelist if configured, else default to safe set
        permitted_tools = contact_permitted_tools if contact_permitted_tools else ["search_web", "read_webpage"]

    reply_text = "I'm sorry, I encountered an error processing your message."

    try:
        # 4. Build message history for DeepSeek
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

        # --- STRICT SELF-HEALING HISTORY LOGIC ---
        # DeepSeek/OpenAI requirement:
        # 1. 'tool' messages must follow an 'assistant' message with 'tool_calls'.
        # 2. 'assistant' messages with 'tool_calls' must be followed by 'tool' messages.
        
        cleaned_messages = []
        i = 0
        while i < len(messages):
            m = messages[i]
            
            # Case 1: Assistant with tool calls
            if m["role"] == "assistant" and m.get("tool_calls"):
                call_ids = [tc.get("id") for tc in m["tool_calls"]]
                
                # Look ahead for matching tool results
                tool_results = []
                j = i + 1
                while j < len(messages) and messages[j]["role"] == "tool":
                    tool_results.append(messages[j])
                    j += 1
                
                found_ids = [tr.get("tool_call_id") for tr in tool_results]
                
                # Check if ALL tool calls have a result
                if all(cid in found_ids for cid in call_ids):
                    # Chain is complete, keep it
                    cleaned_messages.append(m)
                    cleaned_messages.extend(tool_results)
                    i = j # Skip to after tool results
                else:
                    # Broken chain! Strip tool_calls from assistant and ignore the tool results
                    print(f"[WA Debug] Cleaning broken tool chain at index {i}")
                    new_m = m.copy()
                    del new_m["tool_calls"]
                    if not new_m.get("content"):
                        new_m["content"] = "Attempting to help..." # Tool-only messages need text if stripped
                    cleaned_messages.append(new_m)
                    i = j # Skip the orphaned tool results
                continue
            
            # Case 2: Orphaned Tool message (no preceding assistant with tool_calls)
            if m["role"] == "tool":
                print(f"[WA Debug] Dropping orphaned tool message at index {i}")
                i += 1
                continue
                
            # Case 3: Normal message
            cleaned_messages.append(m)
            i += 1
            
        messages = cleaned_messages
        # ------------------------------------------

        # Snapshot messages BEFORE AI call to recover clean history if it crashes mid-turn
        history_snapshot = list(messages)
        input_count = len(messages)
        
        # DEBUG: See exactly what we send to DeepSeek
        print(f"[WA Debug] Full Message Payload: {json.dumps(messages, indent=2)}")
        
        # DeepSeek Native Model execution
        result = chat_completion_with_tools(
            messages=messages,
            model_name=model_name,
            allow_tools=True, 
            permitted_tools=permitted_tools,
            context_params={
                "user_id": sender,
                "is_admin": is_admin
            }
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
        # result for error case: Use history_snapshot to avoid saving unfulfilled tool_calls
        result = {"reply": reply_text, "history": history_snapshot + [{"role": "assistant", "content": reply_text}]}

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

