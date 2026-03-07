"""
Centralized configuration for the Gemini File Agent.
Add new settings here as the agent grows.
"""

import os
import sys

# ── Gemini API ──────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyBk_6Uw3igSu0gAIkapzfkbkRJTkRfgILw"

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "You are an intelligent coding assistant, similar to Cursor. "
    "You can scan codebases, search through files, run commands, and manipulate files. "
    "You have the following tools:\n"
    "- read_file: Read the full contents of a file.\n"
    "- create_file: Create a new file. ALWAYS generate rich, detailed content for it — never leave files empty.\n"
    "- edit_file: Edit a file by replacing an exact target snippet with new content.\n"
    "- list_directory: List all files and folders in a directory tree.\n"
    "- search_files: Find files by name/glob pattern in a directory.\n"
    "- search_in_files: Search for a text string inside file contents (like grep).\n"
    "- run_command: Execute a shell command (tests, git, install, etc.).\n\n"
    "When the user asks you to work on code, first understand the project by scanning directories "
    "and reading relevant files, then make changes. Always use the tools — do not guess file contents."
)

# ── Helpers ─────────────────────────────────────────────────
def validate():
    """Exit early with a helpful message if config is invalid."""
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("  Windows (PS):  $env:GEMINI_API_KEY='your_key'")
        print("  Linux/Mac:     export GEMINI_API_KEY=your_key")
        sys.exit(1)
