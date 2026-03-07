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
    "You can scan codebases, search through files, run commands, and manipulate files.\n\n"

    "IMPORTANT RULES:\n"
    "1. Every message includes a [WORKING DIRECTORY] line at the top. This is the user's active project folder. "
    "When the user says 'current directory', 'here', or 'this project', they mean that directory. "
    "Answer immediately with the path — do NOT run a command to find it.\n"
    "2. When creating or reading files, use FULL ABSOLUTE PATHS by joining the working directory with the filename.\n"
    "3. When creating files, ALWAYS generate rich, detailed content — never leave files empty.\n"
    "4. When listing directories, pass the working directory path to list_directory.\n"
    "5. Answer the user's question directly and concisely. Do not over-explain unless asked.\n\n"

    "Available tools:\n"
    "- read_file: Read the full contents of a file.\n"
    "- create_file: Create a new file with content.\n"
    "- edit_file: Edit a file by replacing an exact target snippet with new content.\n"
    "- list_directory: List all files and folders in a directory tree.\n"
    "- search_files: Find files by name/glob pattern in a directory.\n"
    "- search_in_files: Search for a text string inside file contents (like grep).\n"
    "- run_command: Execute a shell command (tests, git, install, etc.).\n"
)

# ── Helpers ─────────────────────────────────────────────────
def validate():
    """Exit early with a helpful message if config is invalid."""
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("  Windows (PS):  $env:GEMINI_API_KEY='your_key'")
        print("  Linux/Mac:     export GEMINI_API_KEY=your_key")
        sys.exit(1)
