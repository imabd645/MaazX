"""
Intent Classifier
Uses a very fast, lightweight Gemini call to determine the user's intent 
before passing the message to the main Tool Agent.
This drastically reduces hallucination by disabling tools on purely conversational inputs.
"""

import google.generativeai as genai
import config

# Use the fast, lightweight model for intent classification
CLASSIFIER_MODEL = config.MODEL_NAME

def classify_intent(user_msg: str) -> str:
    """
    Classifies the user's string message into one of four rigid intents:
        - 'chat': General conversation, greetings, asking for advice/explanation, storytelling.
        - 'task': Requests to write, edit, create, or modify code/files.
        - 'search': Requests to find files, grep text, or answer questions about the repository.
        - 'automation': Requests to run terminal commands, execute scripts, or manage the system.

    Returns the exact lowercase string.
    """
    
    # We purposefully configure a dedicated client just for this burst call
    if not config.DEEPSEEK_API_KEY:
        return "task"
    
    classifier_prompt = f"""
You are an Intent Classifier for an AI Coding Agent. 
You must analyze the user's message and categorize their true intent. 

Respond ONLY with exactly ONE of the following words. Do not add punctuation or explanation:

1. chat
   (The user is saying hello, asking a conceptual question without needing file access, asking for an explanation, or making general conversation.)
   
2. task 
   (The user wants you to write code, edit files, create a new file, fix a bug, change the system, or save/remember a fact into long-term memory.)
   
3. search
   (The user wants you to look up a file, scan the directory structure, grep for a keyword, or answer a question about what is currently inside a codebase/document.)
   
4. automation
   (The user wants you to run a terminal command, execute a script, fetch URL content, or SEND A MESSAGE (e.g. WhatsApp, email) to someone.)

USER MESSAGE:
"{user_msg}"
"""

    try:
        import requests
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": classifier_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 5
        }
        
        headers = {
            "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        intent = data["choices"][0]["message"]["content"].strip().lower()
        
        # Fallback sanitize to ensure it is exactly one of the known enums
        valid_intents = {"chat", "task", "search", "automation"}
        if intent in valid_intents:
            return intent
            
        # If it hallucinates something else despite strict prompt, default to task
        return "task"
        
    except Exception as e:
        print(f"Warning: Intent Classifier failed ({e}). Defaulting to 'task'.")
        return "task"
