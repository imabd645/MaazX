"""
MaazX (formerly DeepSeek) API client for the coding agent.
Handles chat completions and automatically executes local Python tools in a loop
until a final conversational response is returned.
"""

import json
import requests
import concurrent.futures
from typing import Dict, Any, List

import config
from core.tool_registry import get_all_tools, get_tool_by_name

DEEPSEEK_BASE_URL = "https://api.deepseek.com/chat/completions"
OPENAI_BASE_URL   = "https://api.openai.com/v1/chat/completions"
GEMINI_BASE_URL   = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

def build_tool_definitions(whitelist: List[str] = None) -> List[Dict[str, Any]]:
    """Builds OpenAI-compatible tool definitions using inspect."""
    import inspect
    tools_list = []
    registry = get_all_tools()
    for tool_func in registry:
        name = tool_func.__name__
        if whitelist is not None and name not in whitelist: continue
        doc = tool_func.__doc__ or ""
        desc = [l.strip() for l in doc.split('\n') if l.strip()][0] if doc.strip() else f"Execute {name}"
        schema = {"type": "function", "function": {"name": name, "description": desc, "parameters": {"type": "object", "properties": {}, "required": []}}}
        sig = inspect.signature(tool_func)
        for p_name, p in sig.parameters.items():
            if p_name in ["user_id", "is_admin"]: continue
            p_type = "string"
            if p.annotation == int: p_type = "integer"
            elif p.annotation == bool: p_type = "boolean"
            elif p_name in ["max_results", "count"]: p_type = "integer"
            schema["function"]["parameters"]["properties"][p_name] = {"type": p_type, "description": f"Arg: {p_name}"}
            if p.default == inspect.Parameter.empty: schema["function"]["parameters"]["required"].append(p_name)
        if not schema["function"]["parameters"]["required"]: del schema["function"]["parameters"]["required"]
        tools_list.append(schema)
    return tools_list

def _call_ollama_llm(messages: List[Dict[str, Any]], model: str, tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calls local Ollama API with chat completion.
    """
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.0},
        "max_tokens": 4096,
    }
    if tools:
        payload["tools"] = tools

    print(f"[Ollama] API Request (Model: {model})")
    try:
        resp = requests.post(url, json=payload, timeout=300)
        if not resp.ok:
            print(f"OLLAMA API ERROR {resp.status_code}: {resp.text}")
            raise RuntimeError(f"Ollama API Error: {resp.status_code}")
        data = resp.json()
        return data.get("message", {})
    except Exception as e:
        print(f"[Ollama Error] {e}")
        return {"role": "assistant", "content": f"Ollama Error: {str(e)}"}

def _execute_single_tool(tc: Dict[str, Any], context_params: Dict[str, Any]) -> tuple:
    """Helper to execute a single tool. Returns (call_id, fn_name, fn_args, result_str)."""
    fn = tc.get("function", {})
    fn_name = fn.get("name", "")
    call_id = tc.get("id", "")
    
    try:
        fn_args = fn.get("arguments", "{}")
        if isinstance(fn_args, str):
            if not fn_args.strip():
                fn_args = "{}"
            fn_args = json.loads(fn_args)
    except Exception:
        fn_args = {}
        
    tool_func = get_tool_by_name(fn_name)
    if tool_func:
        try:
            import inspect
            sig = inspect.signature(tool_func)
            final_args = fn_args.copy()
            if context_params:
                if "user_id" in sig.parameters and "user_id" not in final_args:
                    final_args["user_id"] = context_params.get("user_id", "global")
                if "is_admin" in sig.parameters and "is_admin" not in final_args:
                    final_args["is_admin"] = context_params.get("is_admin", False)
            result = tool_func(**final_args)
            result_str = str(result)
        except Exception as e:
            result_str = f"Error executing {fn_name}: {str(e)}"
    else:
        result_str = f"Error: Tool '{fn_name}' not found."
        
    return call_id, fn_name, fn_args, result_str

def chat_completion_with_tools_stream(messages: List[Dict[str, Any]], model_name: str = "deepseek-chat", allow_tools: bool = True, permitted_tools: List[str] = None, context_params: Dict[str, Any] = None):
    """
    Yields real-time updates for chat completions with tools.
    """
    import database
    settings = database.load_settings()
    
    provider = settings.get("llm_provider", "deepseek")
    local_model = settings.get("llm_local_model", "qwen2.5-coder:7b")
    
    if not context_params:
        context_params = {}

    schema_tools = build_tool_definitions(whitelist=permitted_tools) if allow_tools else []
    executed_tools_log = []

    for _ in range(20):
        if provider == "ollama":
            # Ollama Streaming
            url = "http://localhost:11434/api/chat"
            payload = {
                "model": local_model,
                "messages": messages,
                "stream": True,
                "options": {"temperature": 0.0},
                "max_tokens": 4096,
            }
            if schema_tools:
                payload["tools"] = schema_tools

            full_content = ""
            tool_calls = []

            with requests.post(url, json=payload, stream=True, timeout=300) as resp:
                for line in resp.iter_lines():
                    if not line: continue
                    chunk = json.loads(line)
                    msg_chunk = chunk.get("message", {})
                    
                    content = msg_chunk.get("content", "")
                    if content:
                        full_content += content
                        yield {"t": "text", "c": content}
                    
                    if msg_chunk.get("tool_calls"):
                        tool_calls.extend(msg_chunk["tool_calls"])

                    if chunk.get("done"):
                        break
            
            message = {"role": "assistant", "content": full_content}
            if tool_calls:
                message["tool_calls"] = tool_calls

        elif provider == "openai":
            # OpenAI Streaming
            api_key = settings.get("openai_api_key") or config.OPENAI_API_KEY
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model_name, "messages": messages, "temperature": 0.0, "stream": True, "max_tokens": 4096}
            if schema_tools:
                payload["tools"] = schema_tools

            full_content = ""
            tool_calls_raw = {}

            with requests.post(OPENAI_BASE_URL, headers=headers, json=payload, stream=True, timeout=120) as resp:
                for line in resp.iter_lines():
                    if not line: continue
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        if line_str == "data: [DONE]": break
                        try:
                            chunk = json.loads(line_str[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                                yield {"t": "text", "c": content}
                            
                            if delta.get("tool_calls"):
                                for tc in delta["tool_calls"]:
                                    idx = tc.get("index", 0)
                                    if idx not in tool_calls_raw:
                                        tool_calls_raw[idx] = {"id": tc.get("id"), "type": "function", "function": {"name": "", "arguments": ""}}
                                    
                                    # Safe access to function delta
                                    f_delta = tc.get("function", {})
                                    if f_delta.get("name"):
                                        tool_calls_raw[idx]["function"]["name"] += f_delta["name"]
                                    if f_delta.get("arguments"):
                                        tool_calls_raw[idx]["function"]["arguments"] += f_delta["arguments"]
                        except: continue

            message = {"role": "assistant", "content": full_content}
            if tool_calls_raw:
                message["tool_calls"] = [v for k, v in sorted(tool_calls_raw.items())]

        elif provider == "gemini":
            # Gemini OpenAI-compatible Streaming
            api_key = settings.get("gemini_api_key") or config.GEMINI_API_KEY
            if not api_key:
                raise ValueError("Gemini API Key is missing. Please set it in Settings.")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model_name, "messages": messages, "temperature": 0.0, "stream": True, "max_tokens": 4096}
            if schema_tools:
                payload["tools"] = schema_tools

            full_content = ""
            tool_calls_raw = {}

            with requests.post(GEMINI_BASE_URL, headers=headers, json=payload, stream=True, timeout=120) as resp:
                if not resp.ok: resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line: continue
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        if line_str == "data: [DONE]": break
                        try:
                            chunk = json.loads(line_str[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                                yield {"t": "text", "c": content}
                            if delta.get("tool_calls"):
                                for tc in delta["tool_calls"]:
                                    idx = tc.get("index", 0)
                                    if idx not in tool_calls_raw:
                                        tool_calls_raw[idx] = {"id": tc.get("id"), "type": "function", "function": {"name": "", "arguments": ""}}
                                    # Safe access to function delta
                                    f_delta = tc.get("function", {})
                                    if f_delta.get("name"):
                                        tool_calls_raw[idx]["function"]["name"] += f_delta["name"]
                                    if f_delta.get("arguments"):
                                        tool_calls_raw[idx]["function"]["arguments"] += f_delta["arguments"]
                        except: continue

            message = {"role": "assistant", "content": full_content}
            if tool_calls_raw:
                message["tool_calls"] = [v for k, v in sorted(tool_calls_raw.items())]

        else:
            # DeepSeek Streaming
            api_key = settings.get("deepseek_api_key") or config.DEEPSEEK_API_KEY
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model_name, "messages": messages, "temperature": 0.0, "stream": True,"max_tokens": 4096,}
            if schema_tools:
                payload["tools"] = schema_tools

            full_content = ""
            tool_calls_raw = {} # To aggregate streaming tool call parts

            with requests.post(DEEPSEEK_BASE_URL, headers=headers, json=payload, stream=True, timeout=120) as resp:
                for line in resp.iter_lines():
                    if not line: continue
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        if line_str == "data: [DONE]": break
                        chunk = json.loads(line_str[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        
                        content = delta.get("content", "")
                        if content:
                            full_content += content
                            yield {"t": "text", "c": content}
                        
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_raw:
                                    tool_calls_raw[idx] = {"id": tc.get("id"), "type": "function", "function": {"name": "", "arguments": ""}}
                                
                                # Safe access to function delta
                                f_delta = tc.get("function", {})
                                if f_delta.get("name"):
                                    tool_calls_raw[idx]["function"]["name"] += f_delta["name"]
                                if f_delta.get("arguments"):
                                    tool_calls_raw[idx]["function"]["arguments"] += f_delta["arguments"]

            message = {"role": "assistant", "content": full_content}
            if tool_calls_raw:
                message["tool_calls"] = [v for k, v in sorted(tool_calls_raw.items())]

        # Process Message (Text or Tools)
        if not message.get("tool_calls"):
            messages.append(message)
            return

        # Model wants to use tools - execute in parallel
        messages.append(message)
        tool_calls_list = message.get("tool_calls", [])
        
        # 1. Immediately yield start events for all tools so UI updates fast
        for tc in tool_calls_list:
            fn = tc.get("function", {})
            fn_name = fn.get("name", "")
            try:
                fn_args = tc.get("function", {}).get("arguments", "{}")
                if isinstance(fn_args, str):
                    if not fn_args.strip(): fn_args = "{}"
                    fn_args = json.loads(fn_args)
            except Exception:
                fn_args = {}
            yield {"t": "tool", "n": fn_name, "a": fn_args}
            executed_tools_log.append({"name": fn_name, "args": fn_args})
            
        # 2. Execute parallelly
        results_by_id = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(tool_calls_list))) as executor:
            future_to_tc = {executor.submit(_execute_single_tool, tc, context_params): tc for tc in tool_calls_list}
            for future in concurrent.futures.as_completed(future_to_tc):
                tc = future_to_tc[future]
                try:
                    call_id, fn_name, fn_args, result_str = future.result()
                    results_by_id[call_id] = result_str
                    # 3. Yield completion event as soon as one thread ends
                    yield {"t": "result", "n": fn_name, "r": result_str}
                except Exception as exc:
                    call_id = tc.get("id", "unknown")
                    fn_name = tc.get("function", {}).get("name", "unknown")
                    results_by_id[call_id] = f"Error executing {fn_name}: {exc}"
                    yield {"t": "result", "n": fn_name, "r": results_by_id[call_id]}
                    
        # 4. Append tool results to message history in the original requested order
        for tc in tool_calls_list:
            call_id = tc.get("id", "")
            fn_name = tc.get("function", {}).get("name", "")
            result_str = results_by_id.get(call_id, f"Error: Tool lost.")
            messages.append({"role": "tool", "tool_call_id": call_id, "name": fn_name, "content": result_str})

def chat_completion_with_tools(messages: List[Dict[str, Any]], model_name: str = "deepseek-chat", allow_tools: bool = True, permitted_tools: List[str] = None, context_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Sends a completion request to the configured LLM provider (DeepSeek or Ollama).
    Executes tool calls locally (in parallel) and returns the final response.
    """
    import database
    settings = database.load_settings()
    
    provider = settings.get("llm_provider", "deepseek")
    local_model = settings.get("llm_local_model", "qwen2.5-coder:7b")
    
    if not context_params:
        context_params = {}

    schema_tools = build_tool_definitions(whitelist=permitted_tools) if allow_tools else []
    executed_tools_log = []

    for _ in range(20):
        if provider == "ollama":
            message = _call_ollama_llm(messages, local_model, schema_tools)
        elif provider == "openai":
            # OpenAI Cloud
            api_key = settings.get("openai_api_key") or config.OPENAI_API_KEY
            if not api_key:
                raise ValueError("OpenAI API Key is missing. Please set it in Settings.")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model_name, "messages": messages, "temperature": 0.0, "max_tokens": 4096}
            if schema_tools: payload["tools"] = schema_tools
            print(f"\n[OpenAI] API Request (Model: {model_name})")
            resp = requests.post(OPENAI_BASE_URL, headers=headers, json=payload, timeout=120)
            if not resp.ok: resp.raise_for_status()
            message = resp.json().get("choices", [{}])[0].get("message", {})
        elif provider == "gemini":
            # Gemini OpenAI-compatible
            api_key = settings.get("gemini_api_key") or config.GEMINI_API_KEY
            if not api_key:
                raise ValueError("Gemini API Key is missing. Please set it in Settings.")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model_name, "messages": messages, "temperature": 0.0, "max_tokens": 4096}
            if schema_tools: payload["tools"] = schema_tools
            print(f"\n[Gemini] API Request (Model: {model_name})")
            resp = requests.post(GEMINI_BASE_URL, headers=headers, json=payload, timeout=120)
            if not resp.ok: resp.raise_for_status()
            message = resp.json().get("choices", [{}])[0].get("message", {})
        else:
            # DeepSeek Cloud (default)
            api_key = settings.get("deepseek_api_key") or config.DEEPSEEK_API_KEY
            if not api_key:
                raise ValueError("DeepSeek API Key is missing. Please set it in Settings.")
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model_name, "messages": messages, "temperature": 0.0, "max_tokens": 4096}
            if schema_tools: payload["tools"] = schema_tools
            print(f"\n[DeepSeek] API Request (Model: {model_name})")
            resp = requests.post(DEEPSEEK_BASE_URL, headers=headers, json=payload, timeout=120)
            if not resp.ok: 
                print(f"[DeepSeek 400 Error JSON]: {resp.text}")
                resp.raise_for_status()
            message = resp.json().get("choices", [{}])[0].get("message", {})
        
        # 1. Did the model just reply with text?
        if not message.get("tool_calls"):
            reply_text = message.get("content", "")
            print(f"[{provider.upper()}] Text Response: {reply_text[:100]}...")
            messages.append({"role": "assistant", "content": reply_text})
            return {
                "reply": reply_text or "Done.",
                "executed_tools": executed_tools_log,
                "history": messages
            }
            
        # 2. Model wants to use tools
        tool_calls_req = message.get("tool_calls", [])
        print(f"[{provider.upper()}] Requested {len(tool_calls_req)} tools.")
        
        if message.get("content") is None:
            message["content"] = ""
            
        messages.append(message)
        
        # Parallel execution
        results_by_id = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(tool_calls_req))) as executor:
            futures_to_tc = {executor.submit(_execute_single_tool, tc, context_params): tc for tc in tool_calls_req}
            for future in concurrent.futures.as_completed(futures_to_tc):
                tc = futures_to_tc[future]
                try:
                    call_id, fn_name, fn_args, result_str = future.result()
                    results_by_id[call_id] = result_str
                    executed_tools_log.append({"name": fn_name, "args": fn_args})
                except Exception as exc:
                    call_id = tc.get("id", "unknown")
                    fn_name = tc.get("function", {}).get("name", "unknown")
                    results_by_id[call_id] = f"Error executing {fn_name}: {exc}"
                    executed_tools_log.append({"name": fn_name, "args": {}})

        # Append the tool's result to history in original order
        for tc in tool_calls_req:
            call_id = tc.get("id", "")
            fn_name = tc.get("function", {}).get("name", "")
            result_str = results_by_id.get(call_id, "Error: Tool execution failed.")
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": fn_name,
                "content": result_str
            })
            
    return {
        "reply": "System Error: Model called tools too many times in a row.",
        "executed_tools": executed_tools_log
    }
