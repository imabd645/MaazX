"""
Web UI for the DeepSeek Coding Agent.
Run:  python web_app.py
"""

import os
import subprocess
import uuid
import datetime
import time
import json
import threading
import re
import requests
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from google.generativeai.types import content_types

import config
import database as db
import openrouter_client
import core.deepseek_client as deepseek_client
from core.gmail_handler import gmail_handler
from core import git_backup
from core import whatsapp_handler
import tools  # noqa — triggers @register_tool decorators
from core.tool_registry import get_all_tools, get_tool_by_name
from core import bridge_manager

app = Flask(__name__, template_folder="templates", static_folder="static")

# Load persisted settings from SQLite
app_settings = db.load_settings()

# ── Agent setup ─────────────────────────────────────────────
config.validate()
# Configure Gemini with DB key if available, else fall back to config
genai_key = app_settings.get("gemini_api_key") or config.GEMINI_API_KEY
if genai_key:
    genai.configure(api_key=genai_key)

# Session tracking
current_session_id = str(uuid.uuid4())[:8]
current_working_dir = app_settings.get("cwd", os.getcwd())

# In-memory message history for DeepSeek/OpenRouter
session_messages = []

def _is_openrouter_model(model_name: str) -> bool:
    return model_name in openrouter_client.OPENROUTER_MODELS

# ── Health & Self-Healing ───────────────────────────────────
# (Endpoints moved to Health & System section below)


# ── Routes ──────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    global session_messages
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    # Dynamic CWD from DB
    settings = db.load_settings()
    current_working_dir = settings.get("cwd", os.getcwd())

    # ── Intent Classifier ───────────────────────────────────
    from core.intent_classifier import classify_intent
    intent = classify_intent(user_msg)
    
    print(f"\n[INTENT CLASSIFIER] Message: '{user_msg}' => Intent: {intent}")
    
    context_msg = f"[CLASSIFIED INTENT: {intent}]\n[WORKING DIRECTORY]: {current_working_dir}\n\n"
    
    # Inject Agent Memories
    memories = db.get_memories()
    if memories:
        context_msg += "[USER MEMORIES & BACKGROUND]\n"
        context_msg += "You MUST adhere to the following facts, preferences, and context established by the user in previous conversations:\n"
        for k, v in memories.items():
            context_msg += f"- {k}: {v}\n"
        context_msg += "\n"

    context_msg += user_msg

    # Save user message to DB
    db.save_chat_message(current_session_id, "user", user_msg)

    current_model = app_settings.get("model_name", config.MODEL_NAME)

    # ── OpenRouter path (Gemma 3:27B etc.) ──────────────────
    if _is_openrouter_model(current_model):
        api_key = app_settings.get("openrouter_api_key", "")
        if not api_key:
            return jsonify({"error": "OpenRouter API key not set. Go to Settings to add it."}), 400

        session_messages.append({"role": "user", "content": context_msg})

        try:
            # Add system message if first message
            msgs = [{"role": "system", "content": config.SYSTEM_INSTRUCTION}] + session_messages
            
            # Disable tools if intent is pure conversational
            if intent == "chat":
                tool_defs = []
            else:
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

            session_messages.append({"role": "assistant", "content": reply_text})
            db.save_chat_message(current_session_id, "assistant", reply_text, executed_tools)

            return jsonify({
                "reply": reply_text or "Done.",
                "tool_calls": executed_tools,
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── DeepSeek path ───────────────────────────────────────
    else:
        allow_tools = (intent != "chat")
        
        session_messages.append({"role": "user", "content": context_msg})
        
        try:
            msgs = [{"role": "system", "content": config.SYSTEM_INSTRUCTION}] + session_messages
            
            result = deepseek_client.chat_completion_with_tools(
                messages=msgs,
                model_name=current_model,
                allow_tools=allow_tools
            )
            
            reply_text = result["reply"]
            executed_tools = result["executed_tools"]
            
            # The chat_completion_with_tools mutates the msgs array by appending tool roles
            # We must sync those appends back to our session_messages (minus the system prompt)
            session_messages.clear()
            session_messages.extend(msgs[1:])
            
            db.save_chat_message(current_session_id, "assistant", reply_text, executed_tools)

            return jsonify({
                "reply": reply_text,
                "tool_calls": executed_tools,
            })

        except Exception as e:
            # Pop the user message so they can retry
            if session_messages and session_messages[-1]["role"] == "user":
                session_messages.pop()
            return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global current_session_id, session_messages
    current_session_id = str(uuid.uuid4())[:8]
    session_messages = []
    return jsonify({"status": "ok", "session": current_session_id})


# (Chat history endpoints moved to Chat History section below)


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
    db.save_settings({"cwd": current_working_dir})
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


@app.route("/api/save_file", methods=["PUT"])
def api_save_file():
    """Saves edited content back to the file system."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
        
    file_path = data.get("path")
    content = data.get("content")
    
    if not file_path:
        return jsonify({"error": "No path provided"}), 400
        
    if content is None:
        return jsonify({"error": "No content provided"}), 400
        
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
        
    if os.path.isdir(file_path):
        return jsonify({"error": "Cannot write to a directory"}), 400
        
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"success": True, "message": "File saved successfully"})
    except Exception as e:
        return jsonify({"error": f"Error saving file: {str(e)}"}), 500


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

# ── Knowledge Base (PDFs/Docs) ──────────────────────────────
from core import knowledge_indexer

# Make sure a folder exists for uploaded KB documents
KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

@app.route("/api/knowledge/upload", methods=["POST"])
def api_upload_knowledge():
    """Upload a document and index it into the Knowledge base."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    filepath = os.path.join(KNOWLEDGE_DIR, file.filename)
    try:
        file.save(filepath)
        # Synchronously index the document right after upload
        result = knowledge_indexer.index_document(filepath)
        if result.get("status") == "error":
            # If indexing failed, we probably don't want to keep the bad file
            try: os.remove(filepath)
            except: pass
            return jsonify(result), 400
            
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/knowledge/list", methods=["GET"])
def api_list_knowledge():
    """List all files available in the Knowledge base."""
    if not os.path.exists(KNOWLEDGE_DIR):
        return jsonify({"files": []})
    
    files = []
    for f in os.listdir(KNOWLEDGE_DIR):
        path = os.path.join(KNOWLEDGE_DIR, f)
        if os.path.isfile(path):
            files.append({
                "filename": f,
                "size": os.path.getsize(path)
            })
    return jsonify({"files": files})

@app.route("/api/knowledge/delete", methods=["POST"])
def api_delete_knowledge():
    """Delete a document from disk and the knowledge vector index."""
    data = request.json
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "Filename required"}), 400
        
    filepath = os.path.join(KNOWLEDGE_DIR, filename)
    try:
        # 1. Remove from vector DB
        knowledge_indexer.delete_document(filename)
        
        # 2. Remove from OS
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({"status": "success", "msg": f"Deleted {filename}"})
        else:
            return jsonify({"status": "error", "error": "File not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# ── Git / Undo ──────────────────────────────────────────────
from core import git_backup

@app.route("/api/undo", methods=["POST"])
def api_undo_action():
    """Reverts the last agent tool action using git checkout."""
    result = git_backup.undo_last_agent_action(current_working_dir)
    return jsonify(result)

# ── Health & System ─────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def api_get_health():
    """Monitor the status of core AI services and the connection bridge."""
    status = {
        "gemini": "online",
        "deepseek": "online",
        "bridge": "offline"
    }

    # 1. Check Gemini
    gemini_key = app_settings.get("gemini_api_key") or config.GEMINI_API_KEY
    if not gemini_key or gemini_key == "YOUR_GEMINI_API_KEY":
        status["gemini"] = "Config Missing"
    
    # 2. Check DeepSeek
    deepseek_key = app_settings.get("deepseek_api_key") or config.DEEPSEEK_API_KEY
    if not deepseek_key or deepseek_key == "sk-deepseek-api-key-here":
        status["deepseek"] = "Config Missing"

    # 3. Check Bridge
    try:
        bridge_res = requests.get("http://127.0.0.1:3000/status", timeout=2)
        if bridge_res.ok:
            status["bridge"] = "online"
        else:
            status["bridge"] = f"Error {bridge_res.status_code}"
    except Exception:
        status["bridge"] = "offline"

    return jsonify(status)

@app.route("/api/restart_bridge", methods=["POST"])
def api_restart_bridge():
    """
    Placeholder for restarting the bridge process.
    """
    print("[System] Bridge restart requested via UI.")
    return jsonify({"success": True, "message": "Restart signal sent. Please check the bridge terminal."})

# ── Chat History ────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
def api_list_history():
    """Return list of all unique chat sessions."""
    sessions = db.get_chat_sessions()
    return jsonify({"sessions": sessions})

@app.route("/api/history/<session_id>", methods=["GET"])
def api_get_history_session(session_id):
    """Return full message history for a specific session."""
    messages = db.get_chat_history(session_id)
    return jsonify({"messages": messages})

@app.route("/api/history/<session_id>", methods=["DELETE"])
def api_delete_history_session(session_id):
    """Delete a specific chat session."""
    try:
        db.delete_chat_session(session_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Gmail Integration ───────────────────────────────────────
@app.route("/api/gmail/auth", methods=["GET"])
def api_gmail_auth():
    """Returns the Google authorization URL."""
    try:
        auth_url = gmail_handler.get_auth_url()
        return jsonify({"auth_url": auth_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/gmail/callback", methods=["GET"])
def api_gmail_callback():
    """Finalizes Gmail login and saves the token."""
    code = request.args.get("code")
    if not code:
        return "Missing code", 400
    try:
        gmail_handler.handle_callback(code)
        return """
        <html><body style="font-family:sans-serif; text-align:center; padding: 50px; background:#0d1117; color:white;">
            <h2 style="color:#4BB543;">✅ Gmail Connected Successfully!</h2>
            <p>You can now close this window and return to the agent.</p>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body></html>
        """
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        print(f"[Gmail] Callback Error:\n{err_msg}")
        return f"""
        <html><body style="font-family:sans-serif; text-align:center; padding: 50px; background:#1a0d0d; color:#ff6b6b;">
            <h2>❌ Gmail Connection Failed</h2>
            <p style="color:white; background:#331111; padding: 20px; border-radius: 8px; text-align:left; font-family:monospace;">
                {str(e)}
            </p>
            <p style="color:#aaa;">Check the terminal for full logs and try again.</p>
        </body></html>
        """, 500

@app.route("/api/gmail/status", methods=["GET"])
def api_gmail_status():
    """Checks if Gmail is authenticated."""
    service = gmail_handler.get_service()
    return jsonify({"connected": service is not None})

@app.route("/api/gmail/logout", methods=["POST"])
def api_gmail_logout():
    """Clears the Gmail token."""
    settings = db.load_settings()
    if 'gmail_token' in settings:
        del settings['gmail_token']
        db.save_settings(settings)
    return jsonify({"success": True})

# ── WhatsApp Agent ──────────────────────────────────────────

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


def is_port_in_use(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

if __name__ == "__main__":
    # 0. Single Instance Lock
    if is_port_in_use(5000):
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, "Gemini AI Agent is already running!", "Agent Error", 0x10)
        os._exit(1)

    # 1. Start WhatsApp Bridge (Node.js)
    bridge_manager.start_bridge()
    
    # 2. Start Background Scheduler
    import core.scheduler
    core.scheduler.start_scheduler()
    
    print("\n>>> Agent Web UI starting at http://localhost:5000\n")
    app.run(debug=False, port=5000)
