"""
Web UI for the Gemini Coding Agent.
Run:  python web_app.py
"""

import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from google.generativeai.types import content_types

import config
import tools  # noqa — triggers @register_tool decorators
from core.tool_registry import get_all_tools

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── Agent setup ─────────────────────────────────────────────
config.validate()
genai.configure(api_key=config.GEMINI_API_KEY)

_tools = get_all_tools()
model = genai.GenerativeModel(
    model_name=config.MODEL_NAME,
    tools=_tools,
    system_instruction=config.SYSTEM_INSTRUCTION,
)

tool_cfg = content_types.to_tool_config(
    {"function_calling_config": {"mode": "any"}}
)

chat = model.start_chat(enable_automatic_function_calling=True)

# Current working directory for the agent (default: where the script runs)
current_working_dir = os.getcwd()


# ── Routes ──────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    global current_working_dir
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    # Prepend the current working directory context so the model knows where to operate
    context_msg = (
        f"[WORKING DIRECTORY]: {current_working_dir}\n\n"
        f"{user_msg}"
    )

    try:
        response = chat.send_message(context_msg, tool_config=tool_cfg)

        # Try to get text reply
        reply_text = None
        try:
            if response.text:
                reply_text = response.text
        except (ValueError, AttributeError):
            pass

        # Fallback: pull last tool result from history
        if not reply_text:
            for content in reversed(chat.history):
                for part in content.parts:
                    fn_resp = getattr(part, "function_response", None)
                    if fn_resp:
                        result = fn_resp.response.get("result")
                        if result:
                            reply_text = str(result)
                            break
                if reply_text:
                    break

        # Collect tool calls that were made (for showing in the UI)
        tool_calls = []
        for content in chat.history[-6:]:
            for part in content.parts:
                fn_call = getattr(part, "function_call", None)
                if fn_call:
                    tool_calls.append({
                        "name": fn_call.name,
                        "args": dict(fn_call.args) if fn_call.args else {},
                    })

        return jsonify({
            "reply": reply_text or "Done.",
            "tool_calls": tool_calls[-5:],
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global chat
    chat = model.start_chat(enable_automatic_function_calling=True)
    return jsonify({"status": "ok"})


@app.route("/api/cwd", methods=["GET"])
def api_get_cwd():
    """Return the current working directory."""
    return jsonify({"cwd": current_working_dir})


@app.route("/api/cwd", methods=["POST"])
def api_set_cwd():
    """Set a new working directory."""
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
    """List subdirectories of a given path for the directory picker."""
    data = request.get_json()
    path = data.get("path", "").strip()

    # Default to drives on Windows, root on Linux
    if not path:
        if os.name == "nt":
            import string
            drives = []
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
            return jsonify({"parent": "", "dirs": drives})
        else:
            path = "/"

    if not os.path.isdir(path):
        return jsonify({"error": f"'{path}' is not a valid directory"}), 400

    try:
        entries = []
        for entry in sorted(os.listdir(path)):
            full = os.path.join(path, entry)
            if os.path.isdir(full) and not entry.startswith('.'):
                entries.append(full)
        parent = os.path.dirname(os.path.abspath(path))
        return jsonify({"parent": parent, "dirs": entries})
    except PermissionError:
        return jsonify({"error": "Permission denied"}), 403

import subprocess

# Shared terminal history so agent's run_command calls also show up in the UI terminal
terminal_history = []


@app.route("/api/terminal", methods=["POST"])
def api_terminal():
    """Run a command from the UI terminal."""
    global current_working_dir
    data = request.get_json()
    command = data.get("command", "").strip()
    if not command:
        return jsonify({"error": "Empty command"}), 400

    # Handle 'cd' specially — update the working directory
    if command.strip().startswith("cd "):
        new_dir = command.strip()[3:].strip().strip('"').strip("'")
        target = os.path.abspath(os.path.join(current_working_dir, new_dir))
        if os.path.isdir(target):
            current_working_dir = target
            entry = {"command": command, "output": f"Changed directory to {target}", "exit_code": 0, "cwd": current_working_dir}
            terminal_history.append(entry)
            return jsonify(entry)
        else:
            entry = {"command": command, "output": f"cd: no such directory: {new_dir}", "exit_code": 1, "cwd": current_working_dir}
            terminal_history.append(entry)
            return jsonify(entry)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=current_working_dir,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr

        entry = {
            "command": command,
            "output": output.strip() or "(no output)",
            "exit_code": result.returncode,
            "cwd": current_working_dir,
        }
        terminal_history.append(entry)
        return jsonify(entry)

    except subprocess.TimeoutExpired:
        entry = {"command": command, "output": "Command timed out after 60 seconds.", "exit_code": -1, "cwd": current_working_dir}
        terminal_history.append(entry)
        return jsonify(entry)
    except Exception as e:
        entry = {"command": command, "output": str(e), "exit_code": -1, "cwd": current_working_dir}
        terminal_history.append(entry)
        return jsonify(entry)


@app.route("/api/terminal/history", methods=["GET"])
def api_terminal_history():
    """Return recent terminal history (last 50 entries)."""
    return jsonify({"history": terminal_history[-50:], "cwd": current_working_dir})


if __name__ == "__main__":
    print("\n>>> Agent Web UI starting at http://localhost:5000\n")
    app.run(debug=False, port=5000)
