"""
Web UI for the MaazX Coding Agent.
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
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
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

# Session tracking — persist across restarts
current_session_id = app_settings.get("current_session_id", str(uuid.uuid4())[:8])
if "current_session_id" not in app_settings:
    app_settings["current_session_id"] = current_session_id
    db.save_settings({"current_session_id": current_session_id})
current_working_dir = app_settings.get("cwd", os.getcwd())

# Restore in-memory message history from DB so LLM has context after restart
def _restore_session_messages(session_id):
    """Rebuild session_messages list from saved chat history."""
    rows = db.get_chat_history(session_id, limit=50)
    msgs = []
    for row in rows:
        msgs.append({"role": row["role"], "content": row["content"]})
    return msgs

session_messages = _restore_session_messages(current_session_id)

# Abort flag for stopping SSE streaming mid-response
_abort_chat = threading.Event()

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
    _abort_chat.clear()  # Reset abort flag at start of each request
    
    # ── Memory Summarization ──
    from core.memory_summarizer import summarize_if_needed
    summarize_if_needed("chat", current_session_id)
    # Reload session messages in case old ones were pruned
    session_messages = _restore_session_messages(current_session_id)
    
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    chat_mode = data.get("chat_mode", "auto")
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    settings = db.load_settings()
    current_working_dir = settings.get("cwd", os.getcwd())

    # ── Chat Mode Override ──
    from core.intent_classifier import classify_intent
    if chat_mode == "chat":
        intent = "chat"  # Force tools off
    elif chat_mode == "action":
        intent = "task"  # Force tools on
    else:
        intent = classify_intent(user_msg) # Auto mode
        
    # ── Auto-Correction Learner (Background) ──
    from core.correction_learner import extract_and_save_correction
    threading.Thread(target=extract_and_save_correction, args=(user_msg, current_session_id), daemon=True).start()
    
    # Fetch memories for injection
    owner_name = settings.get("wa_owner_name", "User")
    memories = db.get_memories(user_id=owner_name, include_global=True)
    memory_context = ""
    if memories:
        memory_context = "\n\nMy Long-Term Memories:\n" + "\n".join([f"- {k}: {v}" for k,v in memories.items()])
    
    context_msg = user_msg + memory_context
    
    db.save_chat_message(current_session_id, "user", user_msg)

    current_model = app_settings.get("model_name", config.MODEL_NAME)

    # ── SSE Streaming Generator ──────────────────────────────
    def generate():
        global session_messages
        nonlocal user_msg
        full_reply_text = ""
        all_executed_tools = []
        
        try:
            # Prepare initial message list
            messages = [{"role": "system", "content": config.get_system_instruction()}] + session_messages + [{"role": "user", "content": context_msg}]
            
            # Determine current user context
            owner_name = settings.get("wa_owner_name", "Admin")
            
            stream_gen = deepseek_client.chat_completion_with_tools_stream(
                messages=messages,
                model_name=current_model,
                allow_tools=(intent != "chat"),
                context_params={
                    "user_id": owner_name, # Use owner name as personal memory ID for dashboard
                    "is_admin": True       # Local dashboard user is ALWAYS admin
                }
            )

            for chunk in stream_gen:
                # Check if user requested abort
                if _abort_chat.is_set():
                    yield f"data: {json.dumps({'t': 'text', 'c': '\n\n*[Response stopped by user]*'})}\n\n"
                    full_reply_text += "\n\n*[Response stopped by user]*"
                    break

                if chunk["t"] == "text":
                    full_reply_text += chunk["c"]
                elif chunk["t"] == "tool":
                    all_executed_tools.append({"name": chunk["n"], "args": chunk["a"]})
                
                # yield SSE format
                yield f"data: {json.dumps(chunk)}\n\n"

            # Fallback if model was silent after tool calls
            if not full_reply_text and all_executed_tools:
                full_reply_text = "I've completed the requested actions."
                yield f"data: {json.dumps({'t': 'text', 'c': '\n\n' + full_reply_text})}\n\n"

            # Finalize session history by capturing the UPDATED message list
            new_session_history = messages[1:]
            
            # Ensure the last assistant message has the content we just generated if it was empty
            if new_session_history and new_session_history[-1]["role"] == "assistant":
                if not new_session_history[-1].get("content") and full_reply_text:
                    new_session_history[-1]["content"] = full_reply_text
            
            session_messages = new_session_history
            
            # Save final conversational turn to DB history
            db.save_chat_message(current_session_id, "assistant", full_reply_text, all_executed_tools)

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/api/chat/abort", methods=["POST"])
def api_chat_abort():
    """Signal the SSE generator to stop streaming."""
    _abort_chat.set()
    return jsonify({"status": "abort_requested"})


@app.route("/api/session", methods=["GET"])
def api_get_session():
    """Return the current session ID and its saved chat messages for restoring on page load."""
    messages = db.get_chat_history(current_session_id, limit=200)
    return jsonify({"session_id": current_session_id, "messages": messages})


# ── Database GUI ──────────────────────────────────────────────
import sqlite3

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.route("/api/db/list", methods=["GET"])
def api_db_list():
    """Find local SQLite databases in the CWD up to depth 3."""
    db_files = []
    base_depth = current_working_dir.count(os.sep)
    for root, dirs, files in os.walk(current_working_dir):
        # Limit depth to 3 levels to avoid traversing huge codebases for .db
        if root.count(os.sep) - base_depth > 2:
            dirs[:] = []
            continue
        for f in files:
            if f.endswith(".db") or f.endswith(".sqlite"):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, current_working_dir)
                try:
                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                except Exception as e:
                    size_mb = 0.0
                db_files.append({"path": full_path, "name": f, "rel_path": rel_path, "size_mb": round(size_mb, 2)})
    return jsonify({"databases": sorted(db_files, key=lambda x: x['name'])})

@app.route("/api/db/info", methods=["GET"])
def api_db_info():
    """Get all tables and row counts for a specific SQLite database."""
    db_path = request.args.get("db")
    if not db_path or not os.path.exists(db_path):
        return jsonify({"error": "Database not found"}), 404
        
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cur.fetchall()]
        
        table_info = []
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM `{t}`")
                count = cur.fetchone()[0]
                table_info.append({"name": t, "row_count": count})
            except:
                table_info.append({"name": t, "row_count": "?"})
            
        conn.close()
        return jsonify({"tables": table_info})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/db/table", methods=["GET"])
def api_db_table():
    """Fetch schema columns and initial rows for a table."""
    db_path = request.args.get("db")
    table = request.args.get("table")
    limit = request.args.get("limit", 100, type=int)
    
    if not db_path or not os.path.exists(db_path):
        return jsonify({"error": "Database not found"}), 404
        
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = _dict_factory
        cur = conn.cursor()
        
        # Get schema
        cur.execute(f"PRAGMA table_info(`{table}`)")
        columns = [row for row in cur.fetchall()]
        
        # Get data
        cur.execute(f"SELECT * FROM `{table}` LIMIT ?", (limit,))
        rows = cur.fetchall()
        
        conn.close()
        return jsonify({"columns": columns, "rows": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/db/query", methods=["POST"])
def api_db_query():
    """Execute arbitrary raw SQL query."""
    data = request.get_json()
    db_path = data.get("db")
    query = data.get("query")
    
    if not db_path or not os.path.exists(db_path):
        return jsonify({"error": "Database not found"}), 404
    if not query:
         return jsonify({"error": "Query is empty"}), 400
         
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = _dict_factory
        cur = conn.cursor()
        
        cur.execute(query)
        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")):
            conn.commit()
            rows_affected = cur.rowcount
            conn.close()
            return jsonify({"message": "Success", "rows_affected": rows_affected, "is_mutation": True})
        else:
            rows = cur.fetchall()
            columns = [{"name": desc[0]} for desc in cur.description] if cur.description else []
            conn.close()
            return jsonify({"columns": columns, "rows": rows, "is_mutation": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Files & Folders ──────────────────────────────────────────


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global current_session_id, session_messages
    current_session_id = str(uuid.uuid4())[:8]
    session_messages = []
    # Persist new session ID so it survives restarts
    db.save_settings({"current_session_id": current_session_id})
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
        # Enforce UTF-8 and replace errors to prevent UnicodeDecodeError on Windows
        result = subprocess.run(command, shell=True, capture_output=True, text=True,
                                timeout=timeout, cwd=current_working_dir, 
                                encoding='utf-8', errors='replace')
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


# ── Auto-Healing Terminal ───────────────────────────────────
@app.route("/api/terminal/auto_heal", methods=["POST"])
def api_terminal_auto_heal():
    """
    Receives a failed terminal command context and streams the AI's 
    fix attempt back via SSE, reusing the main chat pipeline.
    """
    data = request.get_json()
    command = data.get("command", "")
    output = data.get("output", "")
    exit_code = data.get("exit_code", 1)

    # Check if auto-heal is enabled
    settings = db.load_settings()
    if not settings.get("auto_heal_enabled", True):
        return jsonify({"status": "disabled"}), 200

    # Build a focused prompt for the AI
    heal_prompt = (
        f"[AUTO-HEAL] A command just failed in the terminal. "
        f"Analyze the error, identify the root cause, fix the code if possible, "
        f"and explain what you did in one sentence.\n\n"
        f"Failed Command: {command}\n"
        f"Exit Code: {exit_code}\n"
        f"Error Output:\n```\n{output}\n```\n\n"
        f"Working Directory: {current_working_dir}\n"
        f"IMPORTANT: Be concise. Fix the issue if it's a code bug. "
        f"If it's a missing package, install it. If it's a typo in the command, suggest the correct one."
    )

    current_model = app_settings.get("model_name", config.MODEL_NAME)

    def generate():
        try:
            messages = [
                {"role": "system", "content": config.get_system_instruction()},
                {"role": "user", "content": heal_prompt}
            ]

            owner_name = settings.get("wa_owner_name", "Admin")

            stream_gen = deepseek_client.chat_completion_with_tools_stream(
                messages=messages,
                model_name=current_model,
                allow_tools=True,
                context_params={
                    "user_id": owner_name,
                    "is_admin": True
                }
            )

            full_reply = ""
            for chunk in stream_gen:
                if chunk["t"] == "text":
                    full_reply += chunk["c"]
                yield f"data: {json.dumps(chunk)}\n\n"

            # Save the auto-heal interaction to chat history
            db.save_chat_message(current_session_id, "user", f"[Auto-Heal] Terminal error: `{command}`")
            db.save_chat_message(current_session_id, "assistant", full_reply)

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


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


# ── Git Panel API ───────────────────────────────────────────
@app.route("/api/git/status", methods=["GET"])
def api_git_status():
    """Returns branch name, changed files, and ahead/behind counts."""
    try:
        res = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                             cwd=current_working_dir, capture_output=True, text=True)
        if res.returncode != 0:
            return jsonify({"is_repo": False})

        branch_res = subprocess.run(["git", "branch", "--show-current"],
                                    cwd=current_working_dir, capture_output=True, text=True)
        branch = branch_res.stdout.strip() or "HEAD (detached)"

        status_res = subprocess.run(["git", "status", "--porcelain"],
                                    cwd=current_working_dir, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace')
        changed_files = []
        for line in status_res.stdout.strip().split("\n"):
            if not line.strip():
                continue
            status_code = line[:2].strip()
            filepath = line[3:].strip()
            label = "modified"
            if "?" in status_code: label = "untracked"
            elif "A" in status_code: label = "added"
            elif "D" in status_code: label = "deleted"
            elif "R" in status_code: label = "renamed"
            changed_files.append({"file": filepath, "status": status_code, "label": label})

        ahead, behind = 0, 0
        try:
            ab_res = subprocess.run(["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
                                    cwd=current_working_dir, capture_output=True, text=True)
            if ab_res.returncode == 0:
                parts = ab_res.stdout.strip().split()
                if len(parts) == 2:
                    ahead, behind = int(parts[0]), int(parts[1])
        except Exception:
            pass

        return jsonify({"is_repo": True, "branch": branch, "changed_files": changed_files,
                        "changed_count": len(changed_files), "ahead": ahead, "behind": behind})
    except Exception as e:
        return jsonify({"is_repo": False, "error": str(e)})


@app.route("/api/git/commit", methods=["POST"])
def api_git_commit():
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Commit message is required"}), 400
    try:
        subprocess.run(["git", "add", "."], cwd=current_working_dir, capture_output=True, check=True)
        result = subprocess.run(["git", "commit", "-m", message], cwd=current_working_dir,
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            return jsonify({"error": result.stderr.strip() or result.stdout.strip()}), 400
        return jsonify({"success": True, "output": result.stdout.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/git/push", methods=["POST"])
def api_git_push():
    try:
        result = subprocess.run(["git", "push"], cwd=current_working_dir, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=30)
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            return jsonify({"error": output.strip()}), 400
        return jsonify({"success": True, "output": output.strip() or "Push successful"})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Push timed out after 30s"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/git/pull", methods=["POST"])
def api_git_pull():
    try:
        result = subprocess.run(["git", "pull"], cwd=current_working_dir, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=30)
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            return jsonify({"error": output.strip()}), 400
        return jsonify({"success": True, "output": output.strip() or "Pull successful"})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Pull timed out after 30s"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/git/log", methods=["GET"])
def api_git_log():
    try:
        result = subprocess.run(["git", "log", "--oneline", "--format=%H|%s|%an|%ar", "-n", "10"],
                                cwd=current_working_dir, capture_output=True, text=True,
                                encoding='utf-8', errors='replace')
        if result.returncode != 0:
            return jsonify({"commits": []})
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip(): continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({"hash": parts[0][:7], "message": parts[1], "author": parts[2], "date": parts[3]})
        return jsonify({"commits": commits})
    except Exception as e:
        return jsonify({"commits": [], "error": str(e)})

# ── Security Scanner API ────────────────────────────────────
from core.security_scanner import scan_directory

@app.route("/api/security/scan", methods=["GET"])
def api_security_scan():
    try:
        findings = scan_directory(current_working_dir, limit_files=2000)
        return jsonify({"success": True, "findings": findings})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

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

@app.route("/api/tools/list", methods=["GET"])
def api_list_tools():
    """Return names of all registered agent tools (used by the contact editor UI)."""
    tool_funcs = get_all_tools()
    names = sorted(t.__name__ for t in tool_funcs)
    return jsonify({"tools": names})


# ── Chat History ────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
def api_list_history():
    """Return list of all unique chat sessions."""
    sessions = db.get_chat_sessions()
    return jsonify({"sessions": sessions})


@app.route("/api/session/name", methods=["POST"])
def api_set_session_name():
    """Assign or update a human-readable name for a chat session."""
    data = request.get_json() or {}
    session_id = data.get("session_id", "").strip()
    name = data.get("name", "").strip()
    if not session_id or not name:
        return jsonify({"error": "session_id and name are required"}), 400
    db.set_session_name(session_id, name)
    return jsonify({"success": True, "session_id": session_id, "name": name})

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
        data.get("rules", ""),
        1,
        data.get("permitted_tools", "")
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

    # Note: Refactored architecture uses deepseek_client which is stateless.
    # Changing the model name in settings is sufficient for the next chat call.

    return jsonify(app_settings)

@app.route("/api/jobs", methods=["GET"])
def api_get_jobs():
    """Returns all active jobs + history of executed ones."""
    import core.scheduler as scheduler_module
    import sqlite3
    
    active_jobs = scheduler_module.get_all_jobs()
    
    # Also fetch history
    history = []
    try:
        conn = sqlite3.connect(scheduler_module.DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS job_history (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, prompt TEXT, status TEXT, executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("SELECT name, prompt, status, executed_at FROM job_history ORDER BY executed_at DESC LIMIT 10")
        rows = cur.fetchall()
        for r in rows:
            history.append({
                "name": r[0],
                "prompt": r[1],
                "status": r[2],
                "executed_at": r[3]
            })
        conn.close()
    except Exception as e:
        print(f"Error fetching job history: {e}")
        
    return jsonify({
        "jobs": active_jobs,
        "history": history
    })

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
