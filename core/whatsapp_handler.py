"""
Core logic for the WhatsApp AI Agent.
Handles incoming messages, formats conversation history, queries the AI, and sends replies back to the bridge.
"""

import requests
import google.generativeai as genai
import database
import openrouter_client
from config import GEMINI_API_KEY

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

    # 3. Build the System Prompt
    system_prompt = f"""
    You are an AI assistant managing WhatsApp messages on behalf of {owner_name}.
    You are currently talking to: {contact_name} ({sender}).
    
    Specific Rules for this contact:
    {rules}
    
    General Guidelines:
    - You represent {owner_name}. If asked who you are, explain you are {owner_name}'s AI assistant.
    - Keep replies concise, natural, and human-sounding (WhatsApp style).
    - Do not use markdown like bolding (**) overly much, keep it plain.
    - If a message seems urgent, flag it by starting your reply with [URGENT].
    """

    reply_text = "I'm sorry, I encountered an error processing your message."

    try:
        # Check if it's an OpenRouter model or Gemini
        if model_name in openrouter_client.OPENROUTER_MODELS:
            # We must map the history to OpenAI format
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Since the current message is already in history, we don't append it again
            openrouter_key = settings.get("openrouter_api_key", "")
            
            # We aren't passing tools here to keep the WhatsApp replies safe/fast
            choice, tc = openrouter_client.chat_completion(
                openrouter_key,
                openrouter_client.OPENROUTER_MODELS[model_name],
                messages
            )
            reply_text = choice
            
        else:
            # Gemini Model
            if GEMINI_API_KEY:
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
                
                # Convert history to Gemini format (user vs model)
                gemini_history = []
                # Gemini requires 'user' and 'model' roles. Our DB stores 'user' and 'assistant'
                for msg in history[:-1]: # exclude the latest message to pass it as the new prompt
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({"role": role, "parts": [msg["content"]]})
                
                chat = model.start_chat(history=gemini_history)
                response = chat.send_message(body)
                reply_text = response.text
            else:
                reply_text = "Gemini API Key is not configured."

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

