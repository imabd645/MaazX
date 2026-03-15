"""
Agent Engine — sets up the Gemini model, manages the chat loop,
and dispatches tool calls automatically.

NOTE: Do not run this file directly. Use the root  agent.py  as the entry point.
"""

import datetime
import config
from core.deepseek_client import chat_completion_with_tools
from core.intent_classifier import classify_intent

class Agent:
    """Wraps the DeepSeek model with automatic tool-calling and a REPL loop."""

    def __init__(self):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_context = f"\n\n[SYSTEM CLOCK] The current date and time is: {current_time}. Prioritize web search results and timelines over your pre-training data if they conflict."
        
        self.messages = [
            {"role": "system", "content": config.SYSTEM_INSTRUCTION + time_context}
        ]

    # ── public API ──────────────────────────────────────────
    def send(self, message: str) -> str:
        """Send a user message and return the agent's final text reply."""
        
        # Determine intent
        intent = classify_intent(message)
        allow_tools = (intent != "chat")
        
        print(f"[Agent] Classified Intent: {intent}")
        
        self.messages.append({"role": "user", "content": message})
        
        try:
            result = chat_completion_with_tools(
                messages=self.messages,
                model_name=config.MODEL_NAME,
                allow_tools=allow_tools
            )
            return result["reply"]
        except Exception as e:
            # Revert the user message so they can re-try
            self.messages.pop()
            return f"Error connecting to DeepSeek API: {str(e)}"

    def repl(self):
        """Interactive read-eval-print loop."""
        print("\n[Agent] MaazX Coding Agent ready!  Type 'exit' to quit.")
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
