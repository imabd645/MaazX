"""
Web UI for the Gemini Coding Agent.
Run:  python web_app.py
"""

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
    {"function_calling_config": {"mode": "auto"}}
)

chat = model.start_chat(enable_automatic_function_calling=True)


# ── Routes ──────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    try:
        response = chat.send_message(user_msg, tool_config=tool_cfg)

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
        for content in chat.history[-6:]:  # look at recent history
            for part in content.parts:
                fn_call = getattr(part, "function_call", None)
                if fn_call:
                    tool_calls.append({
                        "name": fn_call.name,
                        "args": dict(fn_call.args) if fn_call.args else {},
                    })

        return jsonify({
            "reply": reply_text or "Done.",
            "tool_calls": tool_calls[-5:],  # last 5 tool calls
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global chat
    chat = model.start_chat(enable_automatic_function_calling=True)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("\n🚀 Agent Web UI starting at http://localhost:5000\n")
    app.run(debug=False, port=5000)
