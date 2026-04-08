# Project Memory — MaazX Auto-Generated

> This file is maintained automatically by MaazX. It tracks architectural decisions,
> recent changes, known issues, and open TODOs. Do not delete — the AI reads this to
> remember context between sessions.

---

## Architecture
- Frontend/Backend: Flask-based Web UI (web_app.py)
- Persistence: SQLite database with python-based manager (database.py)
- Endpoints identified: 54 routes (e.g. /, /api/chat, /api/chat/abort, /api/prompt/tune, /api/prompt/view)
- Database Schema: 7 tables (settings, chat_history, terminal_history, whatsapp_contacts, whatsapp_messages, memories, token_usage)
- Core Engines: agent.py, bridge_manager.py, correction_learner.py, deepseek_client.py, git_backup.py, gmail_handler.py, indexer.py, intent_classifier.py, knowledge_indexer.py, memory_summarizer.py, project_memory.py, prompt_tuner.py, scheduler.py, security_scanner.py, sub_agents.py, tool_registry.py, utils.py, whatsapp_handler.py
- Capabilities: 31 tool modules providing OS/Web/Social integration.

## Recent Changes
### Session — 2026-03-19 20:57
### Session — 2026-03-19 20:54
### Session — 2026-03-19 20:54

## Known Issues
*(None recorded yet)*

## TODOs
*(None recorded yet)*
