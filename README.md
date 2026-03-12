# 🤖 DeepSeek AI Agent v3.2 — Ultra-Detailed Technical Specification

> **The Definitive System Documentation**  
> An autonomous, multi-channel engineering agent powered by DeepSeek-V3, Gemini 2.x, and a specialized tool-calling framework.

---

## 🏛 1. High-Level Architecture

The system is built on an **Event-Driven Agentic Core** that bridges standard web protocols (REST) with asynchronous communication channels (WhatsApp/Cron).

### 🔄 Message Logic Flow
1. **Reception**: A message arrives via the Web UI (HTTP POST) or WhatsApp Bridge (Node.js webhook).
2. **Context Assembly**: The system retrieves the last 20-40 messages from `agent_data.db` and injects the current `CWD` and `System Instructions`.
3. **Reasoning**: The DeepSeek-V3 model analyzes the intent. If an action is required, it emits a `tool_call`.
4. **Execution**: The `local_orchestrator` executes the Python function.
5. **Synthesis**: The tool result is fed back to the model for a final conversational response.
6. **Plain-Text Filter**: Outgoing messages pass through `strip_markdown()` to ensure compatibility.

---

## 📡 2. API Reference (Internal REST)

The `web_app.py` server exposes the following endpoints for the frontend and external integrations:

### Core Chat
- `POST /api/chat`: Primary interaction endpoint. Processes user messages and returns AI responses + tool logs.
- `POST /api/reset`: Resets the current in-memory session.

### File & Project Management
- `GET /api/get_cwd`: Returns the current active working directory.
- `POST /api/set_cwd`: Changes the agent's target directory.
- `GET /api/browse`: Returns a list of files/folders for the directory browser.
- `GET /api/project_files`: Returns a recursive tree structure of the current codebase.
- `POST /api/file_content`: Retrieves terminal-safe text content of a specific file.
- `POST /api/save_file`: Writes edited text back to the file system.

### RAG & Knowledge Base
- `POST /api/index_codebase`: Triggers recursive semantic indexing of the project.
- `GET /api/indexing_status`: Returns the percentage completion of the vector index.
- `POST /api/upload_knowledge`: Adds a PDF/Docx to the long-term knowledge base.
- `GET /api/list_knowledge`: Lists all indexed external documents.
- `POST /api/delete_knowledge`: Removes a document from the vector store.

### System & Integration
- `GET /api/get_health`: Returns connectivity status (Online/Offline) for Gemini, DeepSeek, and WA Bridge.
- `POST /api/restart_bridge`: Triggers a restart of the Node.js WhatsApp subprocess.
- `GET /api/gmail/auth`: Starts the OAuth2 flow.
- `GET /api/gmail/status`: Returns current Gmail connection state.

---

## 🗄 3. Database Schema (`agent_data.db`)

The system uses SQLite for persistent state and low-latency history retrieval.

| Table | Primary Columns | Purpose |
|-------|-----------------|---------|
| `settings` | `key`, `value` | Persists API keys, CWD, and Model preferences. |
| `chat_history` | `session`, `role`, `content`, `tool_calls` | Stores Web-based conversation logs. |
| `terminal_history` | `command`, `output`, `exit_code`, `cwd` | Logs every shell command executed by the agent. |
| `whatsapp_contacts`| `phone_number`, `name`, `rules` | Custom personality rules for specific WhatsApp users. |
| `whatsapp_messages`| `phone_number`, `role`, `content` | Persistent bridge history for asynchronous chats. |
| `memories` | `key`, `value` | Long-term "facts" the agent learns about the user. |

---

## 🛠 4. Advanced Technical Configuration

### Customizing the System Instruction
Edit the `SYSTEM_INSTRUCTION` block in `config.py` to change the agent's behavior. The rules follow a **Strict Operational Charter** where acting (`tool_call`) is prioritized over narrating.

### OAuth2 / PKCE Implementation
The Gmail integration avoids static passwords using the **PKCE (Proof Key for Code Exchange)** flow. 
- The `code_verifier` is generated at runtime and stored in the `settings` table.
- Tokens are exchanged and encrypted in the local database.
- `google-auth-oauthlib` manages the secure handshake.

---

## ❗ 5. Troubleshooting & Maintenance

| Issue | Resolution |
|-------|------------|
| **403 Access Blocked** | Your Google Cloud Project must be in "Testing" mode with your email added as a "Test User". |
| **Missing code verifier** | Ensure `web_app.py` is running on `localhost:5000` so the session persistence in SQLite works during the redirect. |
| **Empty Tool List** | Verify `tools/__init__.py` contains `import tools.filename` for every new tool created. |
| **WA Bridge Offline** | Ensure `whatsapp_bridge/index.js` is running via Node.js and that you've scanned the QR code. |

---

## 👨‍💻 6. Security Framework

- **Isolation**: The WhatsApp Bridge runs in a separate Node.js process to prevent crash propagation.
- **Filtering**: `core/utils.py:strip_markdown` prevents injection of formatting artifacts into plain-text channels.
- **Validation**: The `read_file` tool is a mandatory precursor to `edit_file` to prevent blind overwriting of critical system logic.

---

*Documentation Version 3.2 — Updated March 2026*
