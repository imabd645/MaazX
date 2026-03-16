"""
OpenRouter API client for models not available in the Gemini SDK.
Supports Gemma 3:27B and other OpenRouter-hosted models.
"""

import json
import requests

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"

# Map of model IDs to OpenRouter model strings
OPENROUTER_MODELS = {
    "gemma-3-27b": "google/gemma-3-27b-it",
}


def chat_completion(api_key: str, model_id: str, messages: list, tools: list = None):
    """
    Send a chat completion request to OpenRouter.

    Args:
        api_key:   OpenRouter API key
        model_id:  Key from OPENROUTER_MODELS
        messages:  List of {"role": ..., "content": ...} dicts
        tools:     Optional list of tool definitions (OpenAI-style)

    Returns:
        dict with "reply" (str) and "tool_calls" (list)
    """
    model_name = OPENROUTER_MODELS.get(model_id, model_id)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "Gemini Coding Agent",
    }

    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": 4096,
    }

    if tools:
        payload["tools"] = tools

    resp = requests.post(OPENROUTER_BASE, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})

    reply = message.get("content", "")
    tool_calls_raw = message.get("tool_calls", [])

    tool_calls = []
    for tc in tool_calls_raw:
        fn = tc.get("function", {})
        tool_calls.append({
            "name": fn.get("name", ""),
            "args": json.loads(fn.get("arguments", "{}")) if isinstance(fn.get("arguments"), str) else fn.get("arguments", {}),
        })

    return {
        "reply": reply or "Done.",
        "tool_calls": tool_calls,
    }


def build_tool_definitions():
    """
    Build OpenAI-compatible tool definitions for our agent tools.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the full contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {"filepath": {"type": "string", "description": "Absolute path to the file"}},
                    "required": ["filepath"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_file",
                "description": "Create a new file with content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Absolute path for the new file"},
                        "content": {"type": "string", "description": "Content to write to the file"},
                    },
                    "required": ["filepath", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Edit a file by replacing exact target text with new content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Absolute path to the file"},
                        "target_content": {"type": "string", "description": "Exact text to find"},
                        "replacement_content": {"type": "string", "description": "Text to replace with"},
                    },
                    "required": ["filepath", "target_content", "replacement_content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "List all files and folders in a directory tree",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory_path": {"type": "string", "description": "Absolute path to directory"},
                        "max_depth": {"type": "integer", "description": "Max recursion depth (default 3)"},
                    },
                    "required": ["directory_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Find files matching a glob pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory_path": {"type": "string", "description": "Directory to search"},
                        "pattern": {"type": "string", "description": "Glob pattern like *.py"},
                    },
                    "required": ["directory_path", "pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_in_files",
                "description": "Search for text content inside files (grep-like)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory_path": {"type": "string", "description": "Directory to search"},
                        "query": {"type": "string", "description": "Text to search for"},
                        "file_pattern": {"type": "string", "description": "File glob filter (default *)"},
                    },
                    "required": ["directory_path", "query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Execute a shell command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to run"},
                        "working_directory": {"type": "string", "description": "Working directory (default .)"},
                    },
                    "required": ["command"],
                },
            },
        },
    ]
