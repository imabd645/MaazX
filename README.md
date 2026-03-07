# Gemini Coding Agent

A modular, Cursor-like AI coding assistant powered by the **Gemini API**. It can scan codebases, search through files, run shell commands, and create/edit files — all via natural language.

## Project Structure

```
AI Agnet/
├── agent.py                  # ← Entry point — always run THIS file
├── config.py                 # Settings (API key, model, system prompt)
├── requirements.txt
│
├── core/
│   ├── __init__.py
│   ├── agent.py              # Agent class (model + chat REPL)
│   └── tool_registry.py      # @register_tool decorator & registry
│
└── tools/
    ├── __init__.py            # Imports all tool modules
    ├── file_read.py           # read_file
    ├── file_create.py         # create_file
    ├── file_edit.py           # edit_file
    ├── list_directory.py      # list_directory (tree view)
    ├── search_files.py        # search_files (find by name/glob)
    ├── search_in_files.py     # search_in_files (grep-like)
    └── run_command.py         # run_command (shell execution)
```

## Quick Start

```bash
pip install -r requirements.txt
```

Set your Gemini API key:
```powershell
$env:GEMINI_API_KEY="your_key_here"
```

Run the agent:
```bash
python agent.py
```

> ⚠️ Always run the **root** `agent.py`, not `core/agent.py`.

## Available Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read the full contents of a file |
| `create_file` | Create a new file with content |
| `edit_file` | Replace a snippet inside an existing file |
| `list_directory` | List files & folders in a directory tree |
| `search_files` | Find files by name or glob pattern |
| `search_in_files` | Search text inside files (like grep) |
| `run_command` | Run any shell command |

## Adding a New Tool

1. Create a file in `tools/`, e.g. `tools/my_tool.py`:
   ```python
   from core.tool_registry import register_tool

   @register_tool
   def my_tool(arg1: str) -> str:
       """Description of what it does.

       Args:
           arg1: What this argument means.
       """
       return "result"
   ```

2. Import it in `tools/__init__.py`:
   ```python
   import tools.my_tool
   ```

Done — the agent discovers it automatically on next start.

## Example Prompts

- `List all files in F:/my_project`
- `Search for "TODO" in all Python files in this directory`
- `Find files named *.js in F:/webapp`
- `Read the file F:/my_project/main.py`
- `Add error handling to the login function in auth.py`
- `Run the tests with pytest`
