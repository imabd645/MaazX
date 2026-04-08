"""
Project Memory — Long-Term Knowledge Persistence
Maintains a PROJECT.md file in the current working directory that
auto-updates after each completed AI session with architectural
decisions, recent changes, known bugs, and TODOs.
"""

import os
import time
import requests
import database
import config


# ── Constants ────────────────────────────────────────────────────────────────

PROJECT_MD_FILENAME = "PROJECT.md"

TEMPLATE = """\
# Project Memory — MaazX Auto-Generated

> This file is maintained automatically by MaazX. It tracks architectural decisions,
> recent changes, known issues, and open TODOs. Do not delete — the AI reads this to
> remember context between sessions.

---

## Architecture
*(No information yet — will be populated after the first AI session)*

## Recent Changes
*(No changes logged yet)*

## Known Issues
*(None recorded yet)*

## TODOs
*(None recorded yet)*
"""


# ── Read / Write Helpers ──────────────────────────────────────────────────────

def get_project_md_path(cwd: str) -> str:
    return os.path.join(cwd, PROJECT_MD_FILENAME)


def read_project_memory(cwd: str) -> str | None:
    """Return the current PROJECT.md content, or None if it doesn't exist."""
    path = get_project_md_path(cwd)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    return None


def _write_project_memory(cwd: str, content: str):
    """Write content to PROJECT.md."""
    path = get_project_md_path(cwd)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"[ProjectMemory] Write failed: {e}")


def ensure_project_md(cwd: str):
    """Create PROJECT.md with blank template if it doesn't exist yet."""
    if not os.path.exists(get_project_md_path(cwd)):
        _write_project_memory(cwd, TEMPLATE)


# ── LLM Summarizer ───────────────────────────────────────────────────────────

def _call_llm_for_session_summary(session_text: str) -> dict:
    """
    Send the recent session chat history to the LLM and ask it to
    categorize what was built/changed/identified.
    Returns a dict with keys: changes, architecture, issues, todos.
    """
    system_prompt = (
        "You are a technical project archivist. I will give you a summary of a recent AI coding session. "
        "Your job is to extract structured knowledge from it.\n\n"
        "Respond ONLY with a JSON object (no markdown) with these keys:\n"
        '  "changes": [list of bullet strings describing files/features modified or created]\n'
        '  "architecture": [list of key architectural facts discovered or established]\n'
        '  "issues": [list of bugs or limitations found]\n'
        '  "todos": [list of action items or follow-ups mentioned]\n\n'
        "Keep each item short (1 line). Return empty lists if not applicable."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Session log:\n{session_text[:4000]}"}
    ]

    settings = database.load_settings()
    provider = settings.get("llm_provider", "deepseek")
    model_name = settings.get("model_name", "deepseek-chat")

    try:
        if provider == "ollama":
            local_model = settings.get("llm_local_model", "qwen3:8b")
            resp = requests.post("http://localhost:11434/api/chat", json={
                "model": local_model, "messages": messages, "stream": False,
                "options": {"temperature": 0.1}
            }, timeout=90)
            if resp.ok:
                raw = resp.json().get("message", {}).get("content", "")
        else:
            api_key = settings.get(f"{provider}_api_key") or getattr(config, f"{provider.upper()}_API_KEY", "")
            base_urls = {
                "deepseek": "https://api.deepseek.com/chat/completions",
                "openai":   "https://api.openai.com/v1/chat/completions",
                "gemini":   "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            }
            url = base_urls.get(provider, base_urls["deepseek"])
            if provider == "deepseek":
                api_key = settings.get("deepseek_api_key") or config.DEEPSEEK_API_KEY

            resp = requests.post(url, headers={
                "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"
            }, json={"model": model_name, "messages": messages, "temperature": 0.1, "max_tokens": 600}, timeout=45)
            if resp.ok:
                raw = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return {}

        # Strip markdown fences if present
        raw = raw.strip().strip("```json").strip("```").strip()
        import json
        return json.loads(raw)

    except Exception as e:
        print(f"[ProjectMemory] LLM summary failed: {e}")
        return {}


# ── Update Cycle ─────────────────────────────────────────────────────────────

def update_project_memory(session_id: str, cwd: str):
    """
    Called after a session ends. Reads recent chat history, summarizes it
    with the LLM, and updates PROJECT.md.
    """
    if not cwd or not os.path.isdir(cwd):
        return

    # Get recent session messages
    history = database.get_chat_history(session_id, limit=20)
    if not history:
        return

    # Build a text summary of the session
    session_text = ""
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            session_text += f"[{role.upper()}]: {content[:500]}\n\n"

    if len(session_text) < 100:
        return  # Not enough content to summarize

    summary = _call_llm_for_session_summary(session_text)
    if not summary:
        return

    ensure_project_md(cwd)
    current = read_project_memory(cwd) or TEMPLATE

    timestamp = time.strftime("%Y-%m-%d %H:%M")

    def _format_list(items: list) -> str:
        if not items:
            return ""
        return "\n".join(f"- {i}" for i in items if i.strip())

    # Build the new change block
    changes = _format_list(summary.get("changes", []))
    arch    = _format_list(summary.get("architecture", []))
    issues  = _format_list(summary.get("issues", []))
    todos   = _format_list(summary.get("todos", []))

    new_block = f"\n### Session — {timestamp}"
    if changes: new_block += f"\n{changes}"

    # Append to Recent Changes section
    if "## Recent Changes" in current:
        current = current.replace("## Recent Changes\n*(No changes logged yet)*", f"## Recent Changes{new_block}")
        current = current.replace("## Recent Changes\n", f"## Recent Changes{new_block}\n")

    # Append to Architecture section
    if arch and "## Architecture" in current:
        current = current.replace("## Architecture\n*(No information yet — will be populated after the first AI session)*",
                                  f"## Architecture\n{arch}")

    # Append issues
    if issues and "## Known Issues" in current:
        current = current.replace("## Known Issues\n*(None recorded yet)*", f"## Known Issues\n{issues}")

    # Append TODOs
    if todos and "## TODOs" in current:
        current = current.replace("## TODOs\n*(None recorded yet)*", f"## TODOs\n{todos}")

    _write_project_memory(cwd, current)
    print(f"[ProjectMemory] Updated PROJECT.md in {cwd}")


# ── Context Injection ─────────────────────────────────────────────────────────

def inject_into_context(cwd: str) -> str | None:
    """
    Returns a condensed string of PROJECT.md to inject as system context
    at the beginning of a new chat session. Returns None if no memory exists.
    """
    content = read_project_memory(cwd)
    if not content or len(content.strip()) < 50:
        return None

    # Only include the first 3000 chars to avoid bloating the context window
    digest = content[:3000]
    if len(content) > 3000:
        digest += "\n...(truncated)"

    return (
        f"\n\n## PROJECT MEMORY (auto-loaded from PROJECT.md in {cwd}):\n"
        f"{digest}\n"
        "---\nUse this context to understand prior work without re-reading files."
    )
