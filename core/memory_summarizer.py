"""
Conversation Memory Summarization Engine.
Monitors chat and WhatsApp message counts, and automatically summarizes
older messages into the `memories` table to keep the LLM context lean.
"""

import json
import database
import config
import requests


def _call_llm_summarize(messages_text: str) -> str:
    """Send a fast, tool-less request to the LLM to summarize conversation history."""
    
    system_prompt = (
        "You are an expert summarizer. Your goal is to compress a conversation history "
        "into a concise, highly informative summary. Focus on extracting:\n"
        "1. Key facts or user preferences mentioned.\n"
        "2. Major decisions made or conclusions reached.\n"
        "3. Core context that would be needed to continue the conversation.\n"
        "Do NOT include pleasantries, greetings, or meta-commentary. Just return the facts."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please summarize this conversation history:\n\n{messages_text}"}
    ]
    
    settings = database.load_settings()
    provider = settings.get("llm_provider", "deepseek")
    model_name = settings.get("model_name", "deepseek-chat")
    local_model = settings.get("llm_local_model", "qwen2.5-coder:7b")
    
    try:
        if provider == "ollama":
            url = "http://localhost:11434/api/chat"
            payload = {"model": local_model, "messages": messages, "stream": False, "options": {"temperature": 0.0}}
            resp = requests.post(url, json=payload, timeout=60)
            if resp.ok:
                return resp.json().get("message", {}).get("content", "")
        else:
            # For cloud APIs (OpenAI, Gemini, DeepSeek), we use the deepseek_client logic simplified
            # We'll use DeepSeek as the default fallback for summarization if keys exist
            api_key = settings.get(f"{provider}_api_key") or getattr(config, f"{provider.upper()}_API_KEY", "")
            
            if provider == "openai":
                base_url = getattr(config, "OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
            elif provider == "gemini":
                base_url = getattr(config, "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
            else: # deepseek
                base_url = getattr(config, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")
                api_key = settings.get("deepseek_api_key") or config.DEEPSEEK_API_KEY
                
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model_name, "messages": messages, "temperature": 0.0, "max_tokens": 1000}
            
            resp = requests.post(base_url, headers=headers, json=payload, timeout=60)
            if resp.ok:
                return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                print(f"[Summarizer] API Error: {resp.text}")
                
    except Exception as e:
        print(f"[Summarizer] Exception during summarization: {e}")
        
    return ""


def summarize_if_needed(source: str, identifier: str, threshold: int = 50, keep_recent: int = 20):
    """
    Check message counts and compress old history if over the threshold.
    
    Args:
        source: "chat" or "whatsapp"
        identifier: session ID (for chat) or phone number (for WhatsApp)
        threshold: The message count at which summarization triggers
        keep_recent: How many of the newest messages to leave intact
    """
    if source == "chat":
        count = database.count_chat_messages(identifier)
    elif source == "whatsapp":
        count = database.count_wa_messages(identifier)
    else:
        return

    if count <= threshold:
        return  # No need to summarize yet

    num_to_summarize = count - keep_recent
    print(f"\n[Summarizer] Triggers on {source}:{identifier}. Count: {count}. Summarizing oldest {num_to_summarize} msgs.")

    # 1. Fetch oldest messages
    if source == "chat":
        old_msgs = database.get_oldest_chat_messages(identifier, num_to_summarize)
    else:
        old_msgs = database.get_oldest_wa_messages(identifier, num_to_summarize)

    if not old_msgs:
        return

    # 2. Format for LLM
    text_buffer = ""
    for m in old_msgs:
        role = m.get("role", "unknown").upper()
        content = m.get("content", "")
        if role == "TOOL":
            content = f"[Tool Output: {content[:100]}...]"
        elif role == "ASSISTANT" and m.get("tool_calls"):
            content = f"[Called tools: {len(m['tool_calls'])}]" + (f"\n{content}" if content else "")
            
        text_buffer += f"{role}: {content}\n\n"

    # 3. Call LLM to summarize
    new_summary = _call_llm_summarize(text_buffer.strip())
    if not new_summary:
        print("[Summarizer] Failed to generate summary. Aborting prune.")
        return

    # 4. Save to Memories table
    # We retrieve the existing summary to append/contextualize if needed
    user_id = identifier if source == "whatsapp" else "global"  # Web app sessions use global memory namespace by default
    mem_key = f"{source}_summary_{identifier}"
    
    existing_memories = database.get_memories(user_id=user_id, include_global=False)
    existing_summary = existing_memories.get(mem_key, "")

    if existing_summary:
        # Combine old summary with new summary in another quick LLM call to prevent infinite summary bloat
        combined_text = f"OLD SUMMARY:\n{existing_summary}\n\nNEW CONVERSATION EXTRACT:\n{new_summary}"
        final_summary = _call_llm_summarize(combined_text)
        if not final_summary:
            final_summary = new_summary # Fallback
    else:
        final_summary = new_summary

    database.save_memory(mem_key, final_summary, user_id=user_id)
    print(f"[Summarizer] Saved new summary for {mem_key}:\n{final_summary[:100]}...")

    # 5. Delete old messages from DB
    if source == "chat":
        database.delete_oldest_chat_messages(identifier, num_to_summarize)
    else:
        database.delete_oldest_wa_messages(identifier, num_to_summarize)
        
    print(f"[Summarizer] Deleted oldest {num_to_summarize} messages from DB.")
