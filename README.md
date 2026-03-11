<div align="center">

# 🤖 DeepSeek AI Agent v3.1

### *A Next-Generation Autonomous Engineering Agent*

> Bridging the gap between Large Language Models and Local System Operations  
> with a multi-channel communication layer, long-term memory, and 24+ specialized tools.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-v18%2B-green?style=flat-square&logo=nodedotjs)](https://nodejs.org)
[![Flask](https://img.shields.io/badge/Flask-Backend-lightgrey?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-orange?style=flat-square)](https://www.trychroma.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)

[Features](#-features) · [Architecture](#-system-architecture) · [Installation](#-installation) · [Tools](#-tool-reference) · [Security](#-security-charter) · [Roadmap](#-roadmap)

---

</div>

## 📌 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Core Modules](#-core-modules-deep-dive)
  - [Project Explorer & Web UI](#1--project-explorer--web-ui)
  - [Gmail Integration](#2--gmail-integration-high-security)
  - [WhatsApp Admin Bridge](#3--whatsapp-admin-bridge)
  - [Long-Term Memory & RAG](#4--long-term-memory--rag)
- [Tool Reference](#-tool-reference-master-list)
- [Installation & Developer Setup](#%EF%B8%8F-installation--developer-setup)
- [Configuration Reference](#-configuration-reference)
- [Security Charter](#-security-charter--rules)
- [Developer Guide: Adding Tools](#-developer-guide-adding-tools)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🧭 Overview

**DeepSeek AI Agent v3.1** is a fully autonomous, locally-hosted AI engineering assistant built on top of the [DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V3) language model. Unlike cloud-only AI assistants, this agent runs on your own infrastructure and can directly interact with your file system, shell, email, and messaging platforms — all while maintaining persistent memory across sessions.

The agent is designed for **software engineers and power users** who want an AI that can:

- Read, write, search, and refactor code across large projects
- Send and read emails via Gmail's OAuth2 API
- Receive instructions over **WhatsApp** (including shell commands for admin users)
- Answer deep architectural questions by indexing your entire codebase into a **vector database (RAG)**
- Schedule and automate tasks on your local OS

---

## ✨ Features

| Feature | Details |
|---|---|
| 🧠 **Autonomous Reasoning** | Powered by DeepSeek-V3 for complex multi-step planning |
| 🗂️ **File System Control** | Read, write, patch, grep, and navigate local files |
| 📧 **Gmail Integration** | Send and manage emails with OAuth2 PKCE security |
| 💬 **WhatsApp Bridge** | Admin-controlled shell access via WhatsApp messages |
| 🔍 **RAG Memory** | Index PDFs, docs, and source code for contextual answers |
| 🖥️ **Web Dashboard** | Real-time system health, chat history, dark/light mode |
| 🔒 **Role-Based Access** | Admin vs. user privilege separation on all channels |
| 🗓️ **Task Scheduling** | Queue and execute actions on a time-based trigger |
| 🔌 **Extensible Toolset** | Add new tools with a single decorator in under 5 minutes |
| 💾 **Persistent Sessions** | SQLite-backed chat history, no context loss between restarts |

---

## 🏛 System Architecture

The project follows a **Modular Agentic Architecture**, cleanly separating the reasoning core from the tool execution layer and the communication bridges.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Entry Points                             │
│           Web UI (Browser)          WhatsApp (Mobile)                │
└────────────────────┬────────────────────────┬───────────────────────┘
                     │                        │
              Flask Web App            Node.js WA Bridge
              (web_app.py)         (whatsapp_bridge/index.js)
                     │                        │
                     └──────────┬─────────────┘
                                │  Context + Message
                     ┌──────────▼──────────────┐
                     │   DeepSeek-V3 Core       │
                     │  (core/agent.py)         │
                     │  - System prompt         │
                     │  - Tool selection logic  │
                     │  - Multi-turn reasoning  │
                     └──────────┬──────────────┘
                                │  Tool Calls
                     ┌──────────▼──────────────┐
                     │     Tool Registry        │
                     │  (core/tool_registry.py) │
                     └────────────┬────────────┘
              ┌──────────┬────────┴────────┬───────────┐
              │          │                 │           │
         File Ops    Gmail API          Shell OS     RAG
      (tools/fs.py) (tools/gmail.py) (tools/shell.py) (tools/rag.py)
              │          │                 │           │
         Local Disk  Google Cloud    Windows/Linux  ChromaDB
                                                  + Gemini Embeddings
```

**Data Flow Summary:**

1. User sends a message via Web UI or WhatsApp.
2. The relevant bridge forwards the message + session context to the DeepSeek-V3 core.
3. The core reasons about the task and selects one or more tools from the Tool Registry.
4. Tools execute against local disk, Gmail API, OS shell, or ChromaDB and return results.
5. The core synthesizes a final natural-language reply and sends it back through the bridge.

---

## 🌟 Core Modules Deep-Dive

### 1. 📂 Project Explorer & Web UI

The primary human-computer interface for local usage.

**Technology Stack:**
- **Backend**: Flask (Python)
- **Frontend**: Vanilla JS + CSS (zero framework dependencies)
- **Storage**: SQLite via `agent_data.db`

**Key Features:**

- **Real-time Directory Tree**: Visualize any folder on your machine with live file-system updates.
- **System Health Dashboard**: One-click API connectivity checks for DeepSeek, Gmail, and Gemini.
- **Persistent Chat History**: Every session is stored in SQLite and fully searchable.
- **Glassmorphism UI**: Modern, responsive design with native Dark/Light mode toggle.
- **OAuth2 Gmail Connect Button**: Kick off the Gmail authorization flow directly from the dashboard.

**Running the web server:**
```bash
python web_app.py
# Accessible at http://localhost:5000
```

---

### 2. 📧 Gmail Integration (High Security)

Allows the agent to send, read, and manage emails on your behalf.

**Authentication Flow:**

```
User clicks "Connect Gmail"
        │
        ▼
Agent generates PKCE code_verifier + code_challenge
        │
        ▼
Redirect to Google OAuth2 consent screen
        │
        ▼
Google returns auth_code
        │
        ▼
Agent exchanges auth_code + code_verifier for access_token
        │
        ▼
Tokens saved locally in agent_data.db (AES-encrypted)
        │
        ▼
Agent can now send/read emails on your behalf
```

**Security Properties:**

| Property | Details |
|---|---|
| Auth Standard | OAuth2 with PKCE (RFC 7636) |
| Password Storage | ❌ Never stored |
| Token Storage | ✅ Local only (`agent_data.db`) |
| Token Refresh | ✅ Automatic via refresh token |
| Scope | `gmail.send`, `gmail.readonly` (minimal) |

**Email Formatting:**

All outgoing messages automatically strip Markdown syntax (`**bold**`, `*italic*`, `` `code` ``) to ensure clean rendering across all email clients, including legacy plain-text readers.

---

### 3. 💬 WhatsApp Admin Bridge

Enables mobile-first control of the agent via WhatsApp messages.

**Technology:** Node.js + [Baileys](https://github.com/whiskeysockets/baileys) (WhatsApp Web API)

**User Roles:**

| Role | Capabilities | Configuration |
|---|---|---|
| **Admin** | Chat + shell commands + file edits + system restarts | Set in `config.json` |
| **User** | Conversational AI only | Default for all others |

**Admin Commands (via WhatsApp):**

```
/run <shell command>      → Execute any shell command
/edit <file> <patch>      → Apply a code patch to a file
/find <query>             → Search the codebase
/restart                  → Restart the agent process
/status                   → Get system health report
```

**Context Isolation:** WhatsApp and Web UI maintain completely separate conversation histories to prevent context bleeding between channels.

**Starting the bridge:**
```bash
cd whatsapp_bridge
npm install
node index.js
# Scan the QR code in your terminal with WhatsApp
```

---

### 4. 🧠 Long-Term Memory & RAG

Gives the agent the ability to answer deep, context-heavy questions about any document or codebase.

**Technology:**
- **Vector Database:** [ChromaDB](https://www.trychroma.com) (local, no cloud dependency)
- **Embeddings Model:** `models/gemini-embedding-001` (Google AI)
- **Chunking Strategy:** Recursive character splitting (512 tokens, 50-token overlap)

**Indexable Content Types:**

- `.py`, `.js`, `.ts`, `.go`, `.rs` — Source code files
- `.pdf` — Technical documents, specs, research papers
- `.md`, `.txt`, `.docx` — Project documentation
- `.json`, `.yaml` — Configuration files

**Indexing a project:**
```bash
# Via Web UI: click "Index Directory" and select a folder
# Via Agent: "Index the /projects/myapp directory into memory"
# Via CLI:
python tools/rag.py --index /path/to/project
```

**How it works at query time:**
1. User query is embedded using Gemini embeddings.
2. ChromaDB performs a cosine similarity search over indexed chunks.
3. Top-k most relevant chunks are injected into the agent's context window.
4. DeepSeek-V3 answers the question grounded in your actual code/docs.

---

## 🔧 Tool Reference (Master List)

The agent has access to **24+ specialized tools** organized into functional categories.

### 📁 File System Tools

| Tool | Description | Example Prompt |
|---|---|---|
| `read_file` | Read a file's full contents | *"Show me the contents of server.py"* |
| `edit_file` | Overwrite a file with new content | *"Rewrite the login function in auth.py"* |
| `patch_file` | Apply a targeted diff/patch | *"Add input validation to the register endpoint"* |
| `create_file` | Create a new file | *"Create a new utils/logger.py module"* |
| `delete_file` | Delete a file (with confirmation) | *"Remove the old migration script"* |
| `list_directory` | List files and folders in a path | *"What files are in the /api directory?"* |
| `move_file` | Move or rename a file | *"Move config.py to the /core folder"* |

### 🔍 Search Tools

| Tool | Description | Example Prompt |
|---|---|---|
| `grep_search` | Full-text regex search across files | *"Find all usages of the deprecated API"* |
| `find_definition` | Locate where a symbol is defined | *"Where is the `authenticate()` function defined?"* |
| `fuzzy_file_search` | Find files by name pattern | *"Find all test files in the project"* |
| `semantic_search` | RAG-powered semantic search | *"What does the payment module do?"* |

### 📧 Communication Tools

| Tool | Description | Example Prompt |
|---|---|---|
| `gmail_send_email` | Send an email via Gmail | *"Email the weekly report to Abdullah"* |
| `gmail_read_inbox` | Read recent emails | *"What unread emails do I have?"* |
| `gmail_search` | Search emails by query | *"Find emails from Sarah about the API keys"* |
| `gmail_reply` | Reply to an existing thread | *"Reply to John's email with the updated ETA"* |

### 🖥️ System Tools

| Tool | Description | Example Prompt |
|---|---|---|
| `run_command` | Execute a shell command *(Admin only)* | *"Run the test suite"* |
| `get_system_info` | OS, CPU, memory stats | *"What's the current CPU usage?"* |
| `get_running_processes` | List active processes | *"Is the web server still running?"* |
| `kill_process` | Terminate a process by PID | *"Stop the stuck background worker"* |

### 🗄️ Data Tools

| Tool | Description | Example Prompt |
|---|---|---|
| `inspect_database` | Query the SQLite database | *"Who has admin access in the database?"* |
| `index_directory` | Add a folder to RAG memory | *"Index my entire backend project"* |
| `query_memory` | Query indexed RAG content | *"Explain the auth flow based on the code"* |

### ⏰ Automation Tools

| Tool | Description | Example Prompt |
|---|---|---|
| `schedule_action` | Schedule a task for later | *"Run the build script tomorrow at 9am"* |
| `list_scheduled` | View pending scheduled tasks | *"What tasks are scheduled?"* |
| `cancel_scheduled` | Cancel a scheduled task | *"Cancel the midnight backup task"* |

---

## ⚙️ Installation & Developer Setup

### Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Core agent runtime |
| Node.js | v18+ | WhatsApp bridge |
| pip | Latest | Python package management |
| npm | Latest | Node package management |
| Google Cloud Account | — | Gmail API + Gemini Embeddings |

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/deepseek-agent.git
cd deepseek-agent
```

---

### Step 2: Configure Secrets

Create `agent_secrets.env` in the project root:

```env
# ─── LLM API Keys ─────────────────────────────────────────
ANTIGRAVITY_DEEPSEEK_API_KEY=your_deepseek_key_here

# ─── Google / Gemini ──────────────────────────────────────
ANTIGRAVITY_GEMINI_API_KEY=your_gemini_key_here

# ─── Optional: Logging & Monitoring ──────────────────────
LOG_LEVEL=INFO                    # DEBUG | INFO | WARNING | ERROR
AGENT_PORT=5000                   # Web UI port
```

> ⚠️ **Never commit `agent_secrets.env` to version control.** It is already listed in `.gitignore`.

---

### Step 3: Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# Install all dependencies
pip install -r requirements.txt
```

---

### Step 4: Install Node.js Dependencies (WhatsApp Bridge)

```bash
cd whatsapp_bridge
npm install
cd ..
```

---

### Step 5: Configure Admin Users (WhatsApp)

Edit `config.json` to specify which WhatsApp phone numbers have admin privileges:

```json
{
  "whatsapp": {
    "admins": [
      "923001234567",
      "447911123456"
    ]
  },
  "agent": {
    "max_tool_iterations": 10,
    "default_model": "deepseek-chat"
  }
}
```

---

### Step 6: Set Up Gmail OAuth2

1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. Create a new project (or select an existing one).
3. Navigate to **APIs & Services → Library** and enable the **Gmail API**.
4. Navigate to **APIs & Services → Credentials**.
5. Click **Create Credentials → OAuth 2.0 Client IDs**.
6. Select **Desktop App** as the application type.
7. Download the credentials file and rename it to `credentials.json`.
8. Place `credentials.json` in the project root.
9. Start the web server and click **"Connect Gmail"** in the dashboard to complete authorization.

---

### Step 7: Launch the Agent

```bash
# Start the Web UI + Agent Core
python web_app.py

# In a separate terminal, start the WhatsApp bridge
cd whatsapp_bridge && node index.js
```

Open your browser to `http://localhost:5000`.

---

## 📋 Configuration Reference

`config.json` — Full options:

```json
{
  "whatsapp": {
    "admins": ["<phone_numbers_e164_format>"],
    "session_file": "whatsapp_bridge/session.json",
    "reconnect_interval_ms": 5000
  },
  "agent": {
    "max_tool_iterations": 10,
    "default_model": "deepseek-chat",
    "temperature": 0.2,
    "context_window_tokens": 32000
  },
  "rag": {
    "embedding_model": "models/gemini-embedding-001",
    "chunk_size": 512,
    "chunk_overlap": 50,
    "top_k_results": 5,
    "persist_directory": "./chroma_db"
  },
  "web": {
    "port": 5000,
    "host": "0.0.0.0",
    "debug": false,
    "session_secret": "change_this_to_a_random_string"
  },
  "security": {
    "require_absolute_paths": true,
    "strip_markdown_from_email": true,
    "strip_markdown_from_whatsapp": true
  }
}
```

---

## 🔐 Security Charter & Rules

The agent operates under a strict security model to prevent accidental or malicious misuse.

### Rule 1 — Precision Paths
> **Absolute paths ONLY for all file system operations.**

The agent will reject any file operation that uses a relative path. This prevents it from accidentally operating on the wrong directory based on ambiguous context.

```python
# ✅ Accepted
edit_file("/home/user/projects/myapp/server.py", ...)

# ❌ Rejected
edit_file("server.py", ...)
```

### Rule 2 — Safe Communication
> **All outgoing messages are rendered as plain text.**

Markdown formatting (bold, italics, code blocks) is stripped before any email or WhatsApp message is sent, ensuring compatibility with all clients.

### Rule 3 — Admin Lock on Shell Access
> **The `run_command` tool is forbidden for non-admin WhatsApp users.**

If a non-admin user attempts to run a shell command via WhatsApp, the agent politely refuses and does not execute anything.

### Rule 4 — Channel Isolation
> **Conversation history is maintained independently per channel.**

Web UI sessions and WhatsApp sessions never share history. This prevents context confusion and cross-channel information leakage.

### Rule 5 — Confirmation on Destructive Actions
> **The agent always asks for explicit confirmation before deleting files or sending emails.**

Deletions and email sends require a follow-up confirmation message before the action is executed.

---

## 👨‍💻 Developer Guide: Adding Tools

Adding a new tool to the agent is designed to be fast and frictionless.

### Step 1: Create the Tool File

Create a new Python file in the `tools/` directory:

```python
# tools/my_tool.py

from core.tool_registry import register_tool

@register_tool
def get_system_uptime() -> str:
    """
    Returns the current system uptime as a human-readable string.
    
    Use this when the user asks how long the system has been running
    or requests a system health summary.
    
    Returns:
        str: A formatted uptime string (e.g., "3 days, 4 hours, 12 minutes").
    """
    import subprocess
    result = subprocess.run(["uptime", "-p"], capture_output=True, text=True)
    return result.stdout.strip()
```

**Best Practices for Docstrings:**
- The docstring is used by the LLM to decide *when* to call your tool. Write it clearly and include example use cases.
- Always include `Returns:` documentation.
- Mention any preconditions (e.g., "requires Gmail to be connected").

### Step 2: Register the Tool

Add an import to `tools/__init__.py`:

```python
# tools/__init__.py
import tools.fs
import tools.gmail
import tools.shell
import tools.rag
import tools.my_tool        # ← Add this line
```

### Step 3: Test the Tool

Restart the agent and ask it to use your new tool:

```
"What is the current system uptime?"
```

The agent will automatically discover and invoke your tool based on the docstring.

### Tool Signature Guidelines

| Type | Accepted | Not Accepted |
|---|---|---|
| Parameters | `str`, `int`, `float`, `bool`, `list[str]` | Complex custom classes |
| Return type | `str`, `dict`, `list` | Generator, async |
| Side effects | File writes, API calls — fine | Modifying global agent state |

---

## 📁 Project Structure

```
deepseek-agent/
│
├── web_app.py                  # Flask web server entry point
├── config.json                 # Agent configuration
├── requirements.txt            # Python dependencies
├── credentials.json            # Gmail OAuth2 credentials (not committed)
├── agent_secrets.env           # API keys (not committed)
├── agent_data.db               # SQLite: chat history + OAuth tokens
│
├── core/
│   ├── agent.py                # Main agent loop (DeepSeek-V3 integration)
│   ├── tool_registry.py        # @register_tool decorator + tool loader
│   ├── context_manager.py      # Per-channel conversation history
│   └── safety.py               # Path validation, permission checks
│
├── tools/
│   ├── __init__.py             # Tool imports
│   ├── fs.py                   # File system tools
│   ├── search.py               # Grep + semantic search
│   ├── gmail.py                # Gmail API tools
│   ├── shell.py                # OS shell execution
│   ├── rag.py                  # ChromaDB indexing + querying
│   ├── database.py             # SQLite inspection tools
│   └── scheduler.py            # Task scheduling tools
│
├── whatsapp_bridge/
│   ├── index.js                # Node.js Baileys bridge
│   ├── package.json
│   └── session.json            # WhatsApp session (auto-generated)
│
├── static/
│   ├── style.css               # Web UI stylesheet
│   └── app.js                  # Frontend JavaScript
│
├── templates/
│   └── index.html              # Web UI Jinja2 template
│
├── chroma_db/                  # ChromaDB vector store (auto-generated)
│
└── tests/
    ├── test_tools.py
    ├── test_agent.py
    └── test_rag.py
```

---

## 📈 Roadmap

### v3.2 — Q3 2025
- [ ] **Local Llama-3 Support** via [Ollama](https://ollama.com) for fully offline operation
- [ ] **Multi-file Patch Mode** — apply coordinated changes across multiple files in one instruction
- [ ] **Tool Usage Analytics Dashboard** — visualize which tools are invoked most frequently

### v4.0 — Q4 2025
- [ ] **Vision Tools** — Image and video analysis via Gemini 2.0 Pro (`analyze_screenshot`, `describe_diagram`)
- [ ] **Multi-Agent Collaboration** — Spawn sub-agents for parallel task execution
- [ ] **Team Mode** — Multi-user support with per-user tool permissions and shared memory namespaces
- [ ] **Plugin Marketplace** — Install community-contributed tool packs from a registry

### Ongoing
- [ ] Improve RAG chunking strategy for large monorepos
- [ ] Add support for `.ipynb` Jupyter notebooks in RAG indexing
- [ ] Streaming responses in Web UI

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository.
2. **Create a branch**: `git checkout -b feature/my-new-tool`
3. **Make your changes** and add tests in `tests/`.
4. **Run the test suite**: `pytest tests/`
5. **Commit**: `git commit -m "feat: add get_system_uptime tool"`
6. **Push**: `git push origin feature/my-new-tool`
7. **Open a Pull Request** with a clear description of what you added and why.

Please follow the [Conventional Commits](https://www.conventionalcommits.org) format for commit messages.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---



Made with ❤️ by the Abdullah Masood

*If this project helped you, please consider giving it a ⭐*

