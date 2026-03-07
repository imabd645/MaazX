"""
Gemini File Agent — entry point.
Run:  python agent.py
"""

import config

# 1. Validate env
config.validate()

# 2. Import tools so they auto-register via @register_tool
import tools  # noqa: E402  (must come after config.validate)

# 3. Create agent and start REPL
from core.agent import Agent  # noqa: E402

print("Initializing Gemini File Agent...")
agent = Agent()
agent.repl()
