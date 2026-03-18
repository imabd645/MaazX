"""
Auto-Correction Learner
Background process that intercepts user messages to detect if the user
is correcting a mistake the agent made. If so, it extracts the rule and
saves it into the `memories` table to prevent repeated mistakes.
"""

import database
import config
import requests


def _call_llm_correction_extract(user_msg: str, prev_assistant_msg: str) -> str:
    """Send a fast request to the LLM to detect and extract a rule."""
    
    system_prompt = (
        "You are an AI behavior analyzer. Your job is to determine if the user's message "
        "is correcting a mistake or telling the AI how to behave differently in the future.\n\n"
        "If it IS a correction: Output a single, generalized, absolute rule based on the correction.\n"
        "If it IS NOT a correction (just normal chat/commands): Output exactly the word 'NONE'.\n\n"
        "Example 1:\n"
        "User: 'No, stop using camelCase. I told you to use snake_case.'\n"
        "Output: 'Always use snake_case for variables instead of camelCase.'\n\n"
        "Example 2:\n"
        "User: 'Create a new file called app.py'\n"
        "Output: 'NONE'\n\n"
        "Example 3:\n"
        "User: 'You forgot to add comments again.'\n"
        "Output: 'Always add comments to code when writing or modifying it.'"
    )
    
    context = f"PREVIOUS AI MESSAGE:\n{prev_assistant_msg}\n\nUSER'S REPLY:\n{user_msg}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]
    
    settings = database.load_settings()
    provider = settings.get("llm_provider", "deepseek")
    model_name = settings.get("model_name", "deepseek-chat")
    local_model = settings.get("llm_local_model", "qwen2.5-coder:7b")
    
    try:
        if provider == "ollama":
            url = "http://localhost:11434/api/chat"
            payload = {"model": local_model, "messages": messages, "stream": False, "options": {"temperature": 0.0}}
            resp = requests.post(url, json=payload, timeout=30)
            if resp.ok:
                return resp.json().get("message", {}).get("content", "").strip()
        else:
            api_key = settings.get(f"{provider}_api_key") or getattr(config, f"{provider.upper()}_API_KEY", "")
            
            if provider == "openai":
                base_url = getattr(config, "OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
            elif provider == "gemini":
                base_url = getattr(config, "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
            else: # default to deepseek
                base_url = getattr(config, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")
                api_key = settings.get("deepseek_api_key") or config.DEEPSEEK_API_KEY
                
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model_name, "messages": messages, "temperature": 0.0, "max_tokens": 100}
            
            resp = requests.post(base_url, headers=headers, json=payload, timeout=30)
            if resp.ok:
                return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                
    except Exception as e:
        print(f"[CorrectionLearner] API Error: {e}")
        
    return "NONE"


def extract_and_save_correction(user_msg: str, session_id: str):
    """
    Check if the user message is a correction. If so, save the rule to memory.
    Runs asynchronously so it doesn't block the UI.
    """
    try:
        # Get the preceding assistant message for context
        history = database.get_chat_history(session_id, limit=3) # Get last 3 to find prior assistant msg
        prev_assistant_msg = "(No previous context)"
        
        # history is ordered oldest to newest. The very last message might be this user_msg if it was already saved.
        # So we look for the last 'assistant' message
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                prev_assistant_msg = msg.get("content", "")
                break
                
        # Analyze
        rule = _call_llm_correction_extract(user_msg, prev_assistant_msg)
        
        # If it's a valid rule, save it
        if rule and rule.upper() != "NONE" and len(rule) > 10:
            print(f"\\n[CorrectionLearner] Detected correction! Learned rule: '{rule}'")
            import uuid
            key = f"learned_rule_{str(uuid.uuid4())[:6]}"
            settings = database.load_settings()
            owner = settings.get("wa_owner_name", "User")
            database.save_memory(key, f"USER CORRECTION/PREFERENCE: {rule}", user_id=owner)
            
    except Exception as e:
        print(f"[CorrectionLearner] Exception: {e}")
