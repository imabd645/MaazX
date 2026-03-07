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



@app.route("/api/terminal/history", methods=["GET"])
def api_terminal_history():
    history = db.get_terminal_history(50)
    return jsonify({"history": history, "cwd": current_working_dir})


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


if __name__ == "__main__":
    print("\n>>> Agent Web UI starting at http://localhost:5000\n")
    app.run(debug=False, port=5000)
