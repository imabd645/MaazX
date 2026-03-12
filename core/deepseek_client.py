"""
DeepSeek Official API client for the coding agent.
Handles chat completions and automatically executes local Python tools in a loop
until a final conversational response is returned.
"""

import json
import requests
from typing import Dict, Any, List

import config
from core.tool_registry import get_all_tools, get_tool_by_name

DEEPSEEK_BASE_URL = "https://api.deepseek.com/chat/completions"

def build_tool_definitions(whitelist: List[str] = None) -> List[Dict[str, Any]]:
    """
    Builds OpenAI/DeepSeek-compatible JSON schema tool definitions 
    from our locally registered Python functions.
    If whitelist is provided, only tools in the list are included.
    """
    tools = []
    registry = get_all_tools()
    
    for tool_func in registry:
        name = tool_func.__name__
        
        if whitelist is not None and name not in whitelist:
            continue
            
        description = tool_func.__doc__ or ""
        # A simple generation mapping Python args to JSON Schema.
        # In a generic implementation, we'd inspect the signature, 
        # but for our simple string/bool tools, we can approximate it or hardcode.
        
        # We define a base schema
        tool_schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        # Inject known parameters for our standard tools
        if name == "read_file":
            tool_schema["function"]["parameters"]["properties"] = {
                "filepath": {"type": "string", "description": "Absolute path to the file"}
            }
            tool_schema["function"]["parameters"]["required"] = ["filepath"]
            
        elif name == "create_file":
            tool_schema["function"]["parameters"]["properties"] = {
                "filepath": {"type": "string", "description": "Absolute path for the new file"},
                "content": {"type": "string", "description": "Content to write"}
            }
            tool_schema["function"]["parameters"]["required"] = ["filepath", "content"]
            
        elif name == "edit_file":
            tool_schema["function"]["parameters"]["properties"] = {
                "filepath": {"type": "string", "description": "Absolute path to the file"},
                "search_text": {"type": "string", "description": "Exact text to replace"},
                "replacement_text": {"type": "string", "description": "New text"}
            }
            tool_schema["function"]["parameters"]["required"] = ["filepath", "search_text", "replacement_text"]
            
        elif name == "list_directory":
            tool_schema["function"]["parameters"]["properties"] = {
                "dir_path": {"type": "string", "description": "Absolute directory path"}
            }
            tool_schema["function"]["parameters"]["required"] = ["dir_path"]
            
        elif name == "search_in_files":
            tool_schema["function"]["parameters"]["properties"] = {
                "directory": {"type": "string", "description": "Directory to search in"},
                "query": {"type": "string", "description": "Text to search for"},
                "file_extension": {"type": "string", "description": "e.g. .py, .js (optional)"}
            }
            tool_schema["function"]["parameters"]["required"] = ["directory", "query"]
            
        elif name == "run_command":
            tool_schema["function"]["parameters"]["properties"] = {
                "command": {"type": "string", "description": "Shell command to execute"},
                "cwd": {"type": "string", "description": "Working directory (optional)"}
            }
            tool_schema["function"]["parameters"]["required"] = ["command"]
            
        elif name == "semantic_search":
            tool_schema["function"]["parameters"]["properties"] = {
                "query": {"type": "string", "description": "Question or semantic concept to find in codebase"},
                "max_results": {"type": "integer", "description": "Number of results to return (default 5)"}
            }
            tool_schema["function"]["parameters"]["required"] = ["query"]
            
        elif name == "query_knowledge":
            tool_schema["function"]["parameters"]["properties"] = {
                "query": {"type": "string", "description": "Question to ask the knowledge base documents"},
                "max_results": {"type": "integer", "description": "Number of results to return (default 5)"}
            }
            tool_schema["function"]["parameters"]["required"] = ["query"]
            
        elif name == "remember_fact":
            tool_schema["function"]["parameters"]["properties"] = {
                "key": {"type": "string", "description": "Short identifier for the fact"},
                "value": {"type": "string", "description": "The fact or preference details"}
            }
            tool_schema["function"]["parameters"]["required"] = ["key", "value"]
            
        elif name == "forget_fact":
            tool_schema["function"]["parameters"]["properties"] = {
                "key": {"type": "string", "description": "Short identifier to delete"}
            }
            tool_schema["function"]["parameters"]["required"] = ["key"]

        elif name == "list_memories":
            # No arguments needed
            tool_schema["function"]["parameters"]["properties"] = {}
            
        elif name == "patch_file":
            tool_schema["function"]["parameters"]["properties"] = {
                "filepath": {"type": "string", "description": "Absolute path to the file"},
                "replacements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "target_content": {"type": "string", "description": "Exact text to find"},
                            "replacement_content": {"type": "string", "description": "New text"}
                        },
                        "required": ["target_content", "replacement_content"]
                    }
                }
            }
            tool_schema["function"]["parameters"]["required"] = ["filepath", "replacements"]

        elif name == "search_files":
            tool_schema["function"]["parameters"]["properties"] = {
                "directory_path": {"type": "string", "description": "Root directory to search"},
                "pattern": {"type": "string", "description": "Glob pattern (e.g. *.py)"}
            }
            tool_schema["function"]["parameters"]["required"] = ["directory_path", "pattern"]

        elif name == "search_web":
            tool_schema["function"]["parameters"]["properties"] = {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Default 5"}
            }
            tool_schema["function"]["parameters"]["required"] = ["query"]

        elif name == "read_webpage":
            tool_schema["function"]["parameters"]["properties"] = {
                "url": {"type": "string", "description": "URL to fetch"}
            }
            tool_schema["function"]["parameters"]["required"] = ["url"]

        elif name == "take_screenshot":
            tool_schema["function"]["parameters"]["properties"] = {
                "filename": {"type": "string", "description": "Optional name for the file (e.g. 'desktop.png')"},
                "send_to_whatsapp": {"type": "string", "description": "Optional: Phone number or WhatsApp ID to send the image to immediately after capture"}
            }

        elif name == "send_whatsapp":
            tool_schema["function"]["parameters"]["properties"] = {
                "contact_name_or_phone": {"type": "string", "description": "Name or phone ID (e.g. 'Hamna' or '923123456789@c.us')"},
                "message": {"type": "string", "description": "The exact text to send"}
            }
            tool_schema["function"]["parameters"]["required"] = ["contact_name_or_phone", "message"]

        elif name == "schedule_action":
            tool_schema["function"]["parameters"]["properties"] = {
                "prompt": {"type": "string", "description": "Instruction for the future agent"},
                "cron_expression": {"type": "string", "description": "5-part cron string"},
                "description": {"type": "string", "description": "Human label for the task"}
            }
            tool_schema["function"]["parameters"]["required"] = ["prompt", "cron_expression", "description"]
        elif name == "schedule_once":
            tool_schema["function"]["parameters"]["properties"] = {
                "prompt": {"type": "string", "description": "Instruction for the future agent"},
                "run_at": {"type": "string", "description": "Date/Time in YYYY-MM-DD HH:MM:SS format"},
                "description": {"type": "string", "description": "Human label for the task"}
            }
            tool_schema["function"]["parameters"]["required"] = ["prompt", "run_at", "description"]
        
        # ── PC Control Tools ──
        elif name == "lock_pc":
            tool_schema["function"]["parameters"]["properties"] = {}
        elif name == "pc_power_control":
            tool_schema["function"]["parameters"]["properties"] = {
                "action": {"type": "string", "enum": ["shutdown", "restart", "sleep", "cancel"]}
            }
            tool_schema["function"]["parameters"]["required"] = ["action"]
        elif name == "set_pc_volume":
            tool_schema["function"]["parameters"]["properties"] = {
                "level": {"type": "integer", "description": "Volume level (0-100)"}
            }
            tool_schema["function"]["parameters"]["required"] = ["level"]
        elif name == "launch_app":
            tool_schema["function"]["parameters"]["properties"] = {
                "app_name": {"type": "string", "description": "Name of the app to launch"}
            }
            tool_schema["function"]["parameters"]["required"] = ["app_name"]
        elif name == "close_app":
            tool_schema["function"]["parameters"]["properties"] = {
                "app_name": {"type": "string", "description": "Name of the app/process to close"}
            }
            tool_schema["function"]["parameters"]["required"] = ["app_name"]
            
        # ── Git Tools ──
        elif name == "get_database_schema":
            tool_schema["function"]["parameters"]["properties"] = {
                "db_path": {"type": "string", "description": "Name or path of DB (default agent_data.db)"}
            }
            # Optional, so no required

        elif name == "run_sql_query":
            tool_schema["function"]["parameters"]["properties"] = {
                "query": {"type": "string", "description": "SELECT/PRAGMA SQL statement"},
                "db_path": {"type": "string", "description": "Target DB"}
            }
            tool_schema["function"]["parameters"]["required"] = ["query"]
            
        elif name == "save_whatsapp_contact":
            tool_schema["function"]["parameters"]["properties"] = {
                "phone_number": {"type": "string", "description": "ID like '923123456789@c.us'"},
                "name": {"type": "string", "description": "Friendly name"},
                "rules": {"type": "string", "description": "AI behavior rules for this person"}
            }
            tool_schema["function"]["parameters"]["required"] = ["phone_number", "name"]

        elif name == "delete_whatsapp_contact":
            tool_schema["function"]["parameters"]["properties"] = {
                "phone_number": {"type": "string", "description": "WhatsApp ID to remove"}
            }
            tool_schema["function"]["parameters"]["required"] = ["phone_number"]

        elif name == "search_whatsapp_contacts":
            tool_schema["function"]["parameters"]["properties"] = {
                "query": {"type": "string", "description": "Name or partial name to search for"}
            }
            tool_schema["function"]["parameters"]["required"] = ["query"]

        elif name == "clear_whatsapp_history":
            tool_schema["function"]["parameters"]["properties"] = {
                "phone_number": {"type": "string", "description": "Optional WhatsApp ID to clear"}
            }

        elif name == "trim_whatsapp_history":
            tool_schema["function"]["parameters"]["properties"] = {
                "count": {"type": "integer", "description": "Number of recent messages to delete"},
                "phone_number": {"type": "string", "description": "The WhatsApp ID to trim (REQUIRED)"}
            }
            tool_schema["function"]["parameters"]["required"] = ["count", "phone_number"]

        # ── Git Tools ──
        elif name == "git_sync":
            tool_schema["function"]["parameters"]["properties"] = {
                "message": {"type": "string", "description": "Optional commit message"}
            }
        elif name == "get_git_diff":
            tool_schema["function"]["parameters"]["properties"] = {}
        elif name == "create_github_issue":
            tool_schema["function"]["parameters"]["properties"] = {
                "title": {"type": "string", "description": "Title of the issue"},
                "body": {"type": "string", "description": "Body/Description of the issue"}
            }
            tool_schema["function"]["parameters"]["required"] = ["title", "body"]

        # ── Gmail Tools ──
        elif name == "gmail_search_emails":
            tool_schema["function"]["parameters"]["properties"] = {
                "query": {"type": "string", "description": "Search query (e.g. 'from:boss')"},
                "max_results": {"type": "integer", "description": "Default 5"}
            }
            tool_schema["function"]["parameters"]["required"] = ["query"]

        elif name == "gmail_read_email":
            tool_schema["function"]["parameters"]["properties"] = {
                "message_id": {"type": "string", "description": "The unique Gmail message ID"}
            }
            tool_schema["function"]["parameters"]["required"] = ["message_id"]

        elif name == "gmail_send_email":
            tool_schema["function"]["parameters"]["properties"] = {
                "recipient": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Full email message body"}
            }
            tool_schema["function"]["parameters"]["required"] = ["recipient", "subject", "body"]

        else:
            # Generic fallback for any other tools: assume they take a query or try to inspect
            import inspect
            sig = inspect.signature(tool_func)
            for param_name, param in sig.parameters.items():
                p_type = "string"
                if param.annotation == int: p_type = "integer"
                elif param.annotation == bool: p_type = "boolean"
                
                tool_schema["function"]["parameters"]["properties"][param_name] = {
                    "type": p_type,
                    "description": f"Argument {param_name}"
                }
                if param.default == inspect.Parameter.empty:
                    tool_schema["function"]["parameters"]["required"].append(param_name)

        # Clean up empty required arrays which some strict APIs reject
        if not tool_schema["function"]["parameters"]["required"]:
            del tool_schema["function"]["parameters"]["required"]

        tools.append(tool_schema)
        
    return tools


def chat_completion_with_tools(messages: List[Dict[str, Any]], model_name: str = "deepseek-chat", allow_tools: bool = True, permitted_tools: List[str] = None) -> Dict[str, Any]:
    """
    Sends a completion request to DeepSeek.
    If DeepSeek returns tool calls, this function Executes them locally.

    Args:
        messages: The conversation history.
        model_name: Name of the model to use.
        allow_tools: If False, ignores all tools.
        permitted_tools: Optional list of specific tool names to allow (whitelist).
    Returns:
        {"reply": final_text_string, "executed_tools": list_of_dicts}
    """
    import database
    settings = database.load_settings()
    
    api_key = settings.get("deepseek_api_key") or config.DEEPSEEK_API_KEY
    if not api_key or api_key == "sk-deepseek-api-key-here":
        raise ValueError("DeepSeek API Key is missing. Please set it in Settings.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    schema_tools = build_tool_definitions(whitelist=permitted_tools) if allow_tools else []
    
    executed_tools_log = []

    # Loop allows up to 20 sequential tool calls to prevent infinite loops
    for _ in range(20):
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.0,
        }
        
        if schema_tools:
            payload["tools"] = schema_tools

        print(f"\n[DeepSeek] API Request (Model: {model_name})")
        # print(f"[Payload] {json.dumps(payload, indent=2)}")
        
        resp = requests.post(DEEPSEEK_BASE_URL, headers=headers, json=payload, timeout=120)
        
        if not resp.ok:
            print(f"DEEPSEEK API ERROR {resp.status_code}: {resp.text}")
            try:
                err_data = resp.json()
                raise RuntimeError(f"DeepSeek API Error: {err_data}")
            except Exception:
                resp.raise_for_status()
                
        data = resp.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        
        # 1. Did the model just reply with text?
        if not message.get("tool_calls"):
            reply_text = message.get("content", "")
            print(f"[DeepSeek] Text Response: {reply_text[:100]}...")
            messages.append({"role": "assistant", "content": reply_text})
            return {
                "reply": reply_text or "Done.",
                "executed_tools": executed_tools_log,
                "history": messages
            }
            
        # 2. Model wants to use tools
        print(f"[DeepSeek] Requested {len(message.get('tool_calls', []))} tools.")
        # First, append the assistant's tool_calls message to the history 
        # (required by OpenAI spec before appending the tool responses)
        messages.append(message)
        
        tool_calls_req = message.get("tool_calls", [])
        
        for tc in tool_calls_req:
            fn = tc.get("function", {})
            fn_name = fn.get("name", "")
            call_id = tc.get("id", "")
            
            try:
                fn_args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                fn_args = {}
                
            executed_tools_log.append({"name": fn_name, "args": fn_args})
            
            # Execute locally
            tool_func = get_tool_by_name(fn_name)
            if tool_func:
                try:
                    result = tool_func(**fn_args)
                    result_str = str(result)
                except Exception as e:
                    result_str = f"Error executing {fn_name}: {str(e)}"
            else:
                result_str = f"Error: Tool '{fn_name}' not found."
                
            # Append the tool's result to history
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": fn_name,
                "content": result_str
            })
            
    # Fallback if loop hit 10 iterations
    return {
        "reply": "System Error: Model called tools too many times in a row.",
        "executed_tools": executed_tools_log
    }
