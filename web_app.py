"""
Web UI for the Gemini Coding Agent.
Run:  python web_app.py
"""

import os
import subprocess
import uuid
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from google.generativeai.types import content_types

import config
import database as db
import openrouter_client
import tools  # noqa — triggers @register_tool decorators
from core.tool_registry import get_all_tools, get_tool_by_name

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── Agent setup ─────────────────────────────────────────────
config.validate()
genai.configure(api_key=config.GEMINI_API_KEY)

_tools = get_all_tools()

# Load persisted settings from SQLite
app_settings = db.load_settings()

# Session tracking
current_session_id = str(uuid.uuid4())[:8]
current_working_dir = os.getcwd()

# OpenRouter message history (for non-Gemini models)
openrouter_messages = []


def _is_openrouter_model(model_name: str) -> bool:
    return model_name in openrouter_client.OPENROUTER_MODELS


def _build_gemini_model(model_name: str):
    """Create a fresh Gemini model + chat."""
    m = genai.GenerativeModel(
        model_name=model_name,
        tools=_tools,
        system_instruction=config.SYSTEM_INSTRUCTION,
    )
    return m, m.start_chat(enable_automatic_function_calling=True)


# Initialize Gemini model
model, chat = _build_gemini_model(app_settings.get("model_name", config.MODEL_NAME))


# ── Routes ──────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    global current_working_dir, openrouter_messages
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    context_msg = f"[WORKING DIRECTORY]: {current_working_dir}\n\n{user_msg}"

    # Save user message to DB
    db.save_chat_message(current_session_id, "user", user_msg)

    current_model = app_settings.get("model_name", config.MODEL_NAME)

    # ── OpenRouter path (Gemma 3:27B etc.) ──────────────────
    if _is_openrouter_model(current_model):
        api_key = app_settings.get("openrouter_api_key", "")
        if not api_key:
            return jsonify({"error": "OpenRouter API key not set. Go to Settings to add it."}), 400

        openrouter_messages.append({"role": "user", "content": context_msg})

        try:
            # Add system message if first message
            msgs = [{"role": "system", "content": config.SYSTEM_INSTRUCTION}] + openrouter_messages
            tool_defs = openrouter_client.build_tool_definitions()

            result = openrouter_client.chat_completion(api_key, current_model, msgs, tool_defs)

            reply_text = result["reply"]
            tool_calls = result["tool_calls"]

            # If the model wants to call tools, execute them
            executed_tools = []
            for tc in tool_calls:
                tool_fn = get_tool_by_name(tc["name"])
                if tool_fn:
                    try:
                        tool_result = tool_fn(**tc["args"])
                        executed_tools.append({"name": tc["name"], "args": tc["args"]})
                        reply_text += f"\n\n**Tool: {tc['name']}**\n```\n{tool_result}\n```"
                    except Exception as e:
                        reply_text += f"\n\nTool {tc['name']} error: {e}"

            openrouter_messages.append({"role": "assistant", "content": reply_text})
            db.save_chat_message(current_session_id, "assistant", reply_text, executed_tools)

            return jsonify({
                "reply": reply_text or "Done.",
                "tool_calls": executed_tools,
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── Gemini path ─────────────────────────────────────────
    current_tool_cfg = content_types.to_tool_config(
        {"function_calling_config": {"mode": app_settings.get("tool_mode", "any")}}
    )

    try:
        response = chat.send_message(context_msg, tool_config=current_tool_cfg)

        reply_text = None
        try:
            if response.text:
                reply_text = response.text
        except (ValueError, AttributeError):
            pass

        if not reply_text:
            for content_block in reversed(chat.history):
                for part in content_block.parts:
                    fn_resp = getattr(part, "function_response", None)
                    if fn_resp:
                        result = fn_resp.response.get("result")
                        if result:
                            reply_text = str(result)
                            break
                if reply_text:
                    break

        tool_calls = []
        for content_block in chat.history[-6:]:
            for part in content_block.parts:
                fn_call = getattr(part, "function_call", None)
                if fn_call:
                    tool_calls.append({
                        "name": fn_call.name,
                        "args": dict(fn_call.args) if fn_call.args else {},
                    })

        final_reply = reply_text or "Done."
        db.save_chat_message(current_session_id, "assistant", final_reply, tool_calls[-5:])

        return jsonify({
            "reply": final_reply,
            "tool_calls": tool_calls[-5:],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global chat, current_session_id, openrouter_messages
    current_session_id = str(uuid.uuid4())[:8]
    openrouter_messages = []
    model_name = app_settings.get("model_name", config.MODEL_NAME)
    if not _is_openrouter_model(model_name):
        _, chat = _build_gemini_model(model_name)
    return jsonify({"status": "ok", "session": current_session_id})


@app.route("/api/history", methods=["GET"])
def api_history():
    """Return list of past chat sessions."""
    sessions = db.get_chat_sessions()
    return jsonify({"sessions": sessions, "current": current_session_id})


@app.route("/api/history/<session_id>", methods=["GET"])
def api_history_detail(session_id):
    messages = db.get_chat_history(session_id)
    return jsonify({"session": session_id, "messages": messages})


# ── CWD & Browse ────────────────────────────────────────────
@app.route("/api/cwd", methods=["GET"])
def api_get_cwd():
    return jsonify({"cwd": current_working_dir})


@app.route("/api/cwd", methods=["POST"])
def api_set_cwd():
    global current_working_dir
    data = request.get_json()
    new_dir = data.get("cwd", "").strip()
    if not new_dir:
        return jsonify({"error": "Empty directory path"}), 400
    if not os.path.isdir(new_dir):
        return jsonify({"error": f"'{new_dir}' is not a valid directory"}), 400
    current_working_dir = os.path.abspath(new_dir)
    return jsonify({"cwd": current_working_dir})


@app.route("/api/browse", methods=["POST"])
def api_browse():
    data = request.get_json()
    path = data.get("path", "").strip()
    if not path:
        if os.name == "nt":
            import string
            drives = [f"{l}:\\" for l in string.ascii_uppercase if os.path.exists(f"{l}:\\")]
            return jsonify({"parent": "", "dirs": drives})
        else:
            path = "/"
    if not os.path.isdir(path):
        return jsonify({"error": f"'{path}' is not a valid directory"}), 400
    try:
        entries = [os.path.join(path, e) for e in sorted(os.listdir(path))
                   if os.path.isdir(os.path.join(path, e)) and not e.startswith('.')]
        return jsonify({"parent": os.path.dirname(os.path.abspath(path)), "dirs": entries})
    except PermissionError:
        return jsonify({"error": "Permission denied"}), 403


@app.route("/api/project_files", methods=["GET"])
def api_project_files():
    """Recursively scans the current working directory to build a file tree for the Right Sidebar."""
    def build_tree(dir_path, depth=0, max_depth=5):
        if depth > max_depth:
            return []
            
        tree = []
        try:
            entries = sorted(os.listdir(dir_path))
            for e in entries:
                if e in ['.git', '__pycache__', 'node_modules', '.venv', 'venv'] or e.startswith('.'):
                    continue
                    
                full_path = os.path.join(dir_path, e)
                is_dir = os.path.isdir(full_path)
                
                node = {
                    "name": e,
                    "path": full_path,
                    "is_dir": is_dir,
                    "children": build_tree(full_path, depth + 1, max_depth) if is_dir else []
                }
                tree.append(node)
        except PermissionError:
            pass
            
        return tree
        
    try:
        if not current_working_dir or not os.path.exists(current_working_dir):
            return jsonify({"tree": [], "cwd": ""})
            
        tree = build_tree(current_working_dir)
        return jsonify({"tree": tree, "cwd": current_working_dir})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file_content", methods=["GET"])
def api_file_content():
    """Reads a file and returns its textual content for the frontend File Viewer."""
    file_path = request.args.get("path")
    if not file_path:
        return jsonify({"error": "No path provided"}), 400
        
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
        
    if os.path.isdir(file_path):
        return jsonify({"error": "Cannot read a directory"}), 400
        
    try:
        # Check size to prevent locking up the browser
        if os.path.getsize(file_path) > 1024 * 1024 * 5: # 5MB limit
            return jsonify({"error": "File is too large (> 5MB) to view in browser"}), 400
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"content": content, "path": file_path})
    except UnicodeDecodeError:
        return jsonify({"error": "Cannot read binary file contents"}), 400
    except Exception as e:
        return jsonify({"error": f"Error reading file: {str(e)}"}), 500


# ── Terminal ────────────────────────────────────────────────
@app.route("/api/terminal", methods=["POST"])
def api_terminal():
    global current_working_dir
    data = request.get_json()
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"error": "Empty command"}), 400

    if command.strip().startswith("cd "):
        new_dir = command.strip()[3:].strip().strip('"').strip("'")
        target = os.path.abspath(os.path.join(current_working_dir, new_dir))
        if os.path.isdir(target):
            current_working_dir = target
            entry = {"command": command, "output": f"Changed directory to {target}", "exit_code": 0, "cwd": current_working_dir}
        else:
            entry = {"command": command, "output": f"cd: no such directory: {new_dir}", "exit_code": 1, "cwd": current_working_dir}
        db.save_terminal_entry(entry["command"], entry["output"], entry["exit_code"], entry["cwd"])
        return jsonify(entry)

    timeout = app_settings.get("command_timeout", 60)
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True,
                                timeout=timeout, cwd=current_working_dir)
        output = (result.stdout or "") + (result.stderr or "")
        entry = {"command": command, "output": output.strip() or "(no output)",
                 "exit_code": result.returncode, "cwd": current_working_dir}
    except subprocess.TimeoutExpired:
        entry = {"command": command, "output": f"Timed out after {timeout}s.", "exit_code": -1, "cwd": current_working_dir}
    except Exception as e:
        entry = {"command": command, "output": str(e), "exit_code": -1, "cwd": current_working_dir}

    db.save_terminal_entry(entry["command"], entry["output"], entry["exit_code"], entry["cwd"])
    return jsonify(entry)

@app.route("/api/terminal/history", methods=["GET"])
def api_terminal_history():
    history = db.get_terminal_history(50)
    return jsonify({"history": history, "cwd": current_working_dir})


# ── RAG / Indexing ──────────────────────────────────────────
from core import indexer

@app.route("/api/index_codebase", methods=["POST"])
def api_index_codebase():
    """Start indexing the current working directory."""
    if indexer.start_indexing(current_working_dir):
        return jsonify({"status": "started", "msg": f"Started indexing {current_working_dir}"})
    else:
        return jsonify({"status": "already_running", "msg": "Indexing is already in progress"})

@app.route("/api/indexing_status", methods=["GET"])
def api_indexing_status():
    """Get the current RAG indexing progress."""
    return jsonify(indexer.get_indexing_status())

# ── Git / Undo ──────────────────────────────────────────────
from core import git_backup

@app.route("/api/undo", methods=["POST"])
def api_undo_action():
    """Reverts the last agent tool action using git checkout."""
    result = git_backup.undo_last_agent_action(current_working_dir)
    return jsonify(result)

# ── WhatsApp Agent ──────────────────────────────────────────
from core import whatsapp_handler
import threading

@app.route("/api/whatsapp/incoming", methods=["POST"])
def api_whatsapp_incoming():
    """Webhook for Node.js bridge to send incoming WhatsApp messages."""
    data = request.json
    if not data:
        return jsonify({"error": "No payload"}), 400
        
    # Process message in background to not block the Express bridge
    thread = threading.Thread(target=whatsapp_handler.handle_incoming_message, args=(data,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "received"})

@app.route("/api/whatsapp/contacts", methods=["GET"])
def api_get_wa_contacts():
    """Retrieve all customized WhatsApp contacts."""
    contacts = db.get_all_wa_contacts()
    return jsonify(contacts)

@app.route("/api/whatsapp/contacts", methods=["POST"])
def api_save_wa_contact():
    """Save or update a WhatsApp contact rule."""
    data = request.json
    raw_phone = data.get("phone_number", "").strip()
    
    # Robust Backend Sanitization
    import re
    sanitized = re.sub(r'[^0-9c.us@g]', '', raw_phone)
    if sanitized.startswith('0'):
        # Just in case they bypass UI, auto-assume Pakistan (+92) if it starts with 0
        sanitized = "92" + sanitized[1:]
    
    if sanitized and not sanitized.endswith("@c.us") and not sanitized.endswith("@g.us"):
        sanitized += "@c.us"

    db.save_wa_contact(
        sanitized,
        data.get("name", "Unknown Contact"),
        data.get("summary", ""),
        data.get("rules", "")
    )
    return jsonify({"success": True})

@app.route("/api/whatsapp/contacts", methods=["DELETE"])
def api_delete_wa_contact():
    """Delete a customized WhatsApp contact."""
    data = request.json or {}
    phone = data.get("phone_number")
    try:
        if phone:
            db.delete_wa_contact(phone)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/whatsapp/logout", methods=["POST"])
def api_wa_logout():
    """Logs the user out of the WhatsApp bridge session."""
    try:
        res = requests.post("http://127.0.0.1:3000/logout", timeout=10)
        res.raise_for_status()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/whatsapp/history", methods=["DELETE"])
def api_clear_wa_history():
    """Clear message history for a specific contact or all."""
    data = request.json or {}
    phone = data.get("phone_number")
    try:
        db.clear_wa_history(phone)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Settings ────────────────────────────────────────────────
@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify(app_settings)


@app.route("/api/settings", methods=["POST"])
def api_set_settings():
    global model, chat, app_settings, openrouter_messages
    data = request.get_json()

    changed_model = False
    for key in list(db.DEFAULT_SETTINGS.keys()) + ["openrouter_api_key"]:
        if key in data:
            if key == "model_name" and data[key] != app_settings.get("model_name"):
                changed_model = True
            app_settings[key] = data[key]

    # Persist to SQLite
    db.save_settings(app_settings)

    # Rebuild model if needed
    if changed_model:
        new_model = app_settings["model_name"]
        if _is_openrouter_model(new_model):
            openrouter_messages = []
        else:
            try:
                model, chat = _build_gemini_model(new_model)
            except Exception as e:
                return jsonify({"error": f"Failed to switch model: {e}"}), 400

    return jsonify(app_settings)

@app.route("/api/jobs", methods=["GET"])
def api_get_jobs():
    """Returns a list of all scheduled cron jobs."""
    import core.scheduler as scheduler_module
    jobs = scheduler_module.get_all_jobs()
    return jsonify({"jobs": jobs})

@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def api_delete_job(job_id):
    """Deletes a scheduled cron job by ID."""
    import core.scheduler as scheduler_module
    success = scheduler_module.remove_job(job_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to remove job"}), 500


if __name__ == "__main__":
    import core.scheduler
    core.scheduler.start_scheduler()
    
    print("\n>>> Agent Web UI starting at http://localhost:5000\n")
    app.run(debug=False, port=5000)
