import core.deepseek_client as dc
import config
import json

# Force a 400 error by simulating a tool-call history turn
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "List files."},
    {
        "role": "assistant",
        "content": None,  # This might be the 400 trigger!
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "list_directory", "arguments": '{"dir_path": "."}'}
            }
        ]
    },
    {
        "role": "tool",
        "tool_call_id": "call_123",
        "name": "list_directory",
        "content": "file1.txt, file2.txt"
    }
]

print("Testing multi-turn with None content...")
try:
    res = dc.chat_completion_with_tools(messages, allow_tools=True)
    print("Success:", res["reply"])
except Exception as e:
    print("Caught Error:", str(e))
