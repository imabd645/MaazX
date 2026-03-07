"""
Agent Engine — sets up the Gemini model, manages the chat loop,
and dispatches tool calls automatically.

NOTE: Do not run this file directly. Use the root  agent.py  as the entry point.
"""

import google.generativeai as genai
from google.generativeai.types import content_types

import config
from core.tool_registry import get_all_tools


class Agent:
    """Wraps a Gemini model with automatic tool-calling and a REPL loop."""

    def __init__(self):
        # Configure Gemini with the API key from config
        genai.configure(api_key=config.GEMINI_API_KEY)

        tools = get_all_tools()
        if not tools:
            raise RuntimeError("No tools registered. Import your tool modules before creating the Agent.")

        self.model = genai.GenerativeModel(
            model_name=config.MODEL_NAME,
            tools=tools,
            system_instruction=config.SYSTEM_INSTRUCTION,
        )

        # "auto" mode: the model decides when to call a tool vs reply with text.
        # "any" mode: the model MUST call a tool first — action before talking.
        self.tool_config = content_types.to_tool_config(
            {"function_calling_config": {"mode": "any"}}
        )

        # enable_automatic_function_calling lets the SDK
        # execute the Python functions and feed results back to the model
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

    # ── public API ──────────────────────────────────────────
    def send(self, message: str) -> str:
        """Send a user message and return the agent's final text reply."""
        response = self.chat.send_message(message, tool_config=self.tool_config)

        # After automatic function calling the final response may have no
        # text part at all (finish_reason = STOP with zero parts).
        # Safely try .text first, then fall back to the last tool result.
        try:
            if response.text:
                return response.text
        except (ValueError, AttributeError):
            pass

        # Pull the last function-response from chat history so the user
        # can see what the tool actually returned.
        return self._last_tool_result() or "Done."

    def _last_tool_result(self) -> str | None:
        """Walk chat history backwards and return the last function response string."""
        for content in reversed(self.chat.history):
            for part in content.parts:
                if fn_resp := getattr(part, "function_response", None):
                    result = fn_resp.response.get("result")
                    if result:
                        return str(result)
        return None

    def repl(self):
        """Interactive read-eval-print loop."""
        print("\n[Agent] Coding Agent ready!  Type 'exit' to quit.")
        print("   I can scan codebases, search files, run commands, and edit code.\n")

        while True:
            try:
                user_input = input("You: ")
            except (EOFError, KeyboardInterrupt):
                break

            if user_input.strip().lower() in ("exit", "quit"):
                break
            if not user_input.strip():
                continue

            try:
                reply = self.send(user_input)
                print(f"Agent: {reply}")
            except Exception as e:
                print(f"Error: {e}")

        print("Goodbye!")
