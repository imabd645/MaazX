import sys
import os
# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
import tools  # Triggers registration
from core.deepseek_client import chat_completion_with_tools

# Update config for test if needed
# config.WHATSAPP_ADMIN_NUMBERS = ["test@c.us"]

messages = [
    {"role": "system", "content": "You are a helpful assistant with system access. Use tools if needed."},
    {"role": "user", "content": "List the files in the current directory."}
]

print("Starting DeepSeek Tool Call Test...")
try:
    result = chat_completion_with_tools(
        messages=messages,
        model_name="deepseek-chat",
        allow_tools=True
    )
    print("\n[RESULT]")
    print(f"Reply: {result['reply']}")
    print(f"Executed Tools: {result['executed_tools']}")
except Exception as e:
    print(f"Test Failed: {e}")
