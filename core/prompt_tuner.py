"""
Prompt Tuner — Self-Improvement Loop
Analyzes tool failures and user corrections over time, generates improved
behavior rules, and appends them to the live system prompt.
"""

import os
import time
import json
import requests
import database
import config

LEARNED_PROMPT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent_learned_prompt.txt")


# ── Persistence ──────────────────────────────────────────────────────────────

def load_learned_rules() -> str:
    """Read previously learned rules from disk."""
    try:
        if os.path.exists(LEARNED_PROMPT_FILE):
            with open(LEARNED_PROMPT_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def save_learned_rules(rules_text: str):
    """Persist learned rules to disk."""
    try:
        with open(LEARNED_PROMPT_FILE, "w", encoding="utf-8") as f:
            f.write(rules_text)
    except Exception as e:
        print(f"[PromptTuner] Failed to save rules: {e}")


def get_learned_rules_count() -> int:
    """Returns the number of saved improvement rules."""
    text = load_learned_rules()
    if not text:
        return 0
    return len([l for l in text.split("\n") if l.strip().startswith("-")])


# ── Tool Failure Logging ─────────────────────────────────────────────────────

def ensure_tool_log_table():
    """Create the tool_logs table if it doesn't exist."""
    import sqlite3
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tool_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name  TEXT NOT NULL,
            args       TEXT DEFAULT '{}',
            result     TEXT,
            success    INTEGER NOT NULL DEFAULT 1,
            timestamp  REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def log_tool_result(tool_name: str, args: dict, result: str, success: bool):
    """Record a tool execution outcome to the database."""
    try:
        ensure_tool_log_table()
        import sqlite3
        conn = sqlite3.connect(database.DB_PATH)
        conn.execute(
            "INSERT INTO tool_logs (tool_name, args, result, success, timestamp) VALUES (?,?,?,?,?)",
            (tool_name, json.dumps(args, default=str), str(result)[:2000], 1 if success else 0, time.time())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[PromptTuner] log_tool_result error: {e}")


def get_recent_failures(limit: int = 50) -> list:
    """Fetch recent failed tool calls from the database."""
    try:
        ensure_tool_log_table()
        import sqlite3
        conn = sqlite3.connect(database.DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT tool_name, args, result FROM tool_logs WHERE success=0 ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[PromptTuner] get_recent_failures error: {e}")
        return []


# ── LLM Synthesis ────────────────────────────────────────────────────────────

def _call_llm_for_rule(failure_summary: str) -> str:
    """Ask the LLM to derive a self-improvement rule from failure patterns."""
    system_prompt = (
        "You are a meta-AI that improves an AI coding assistant's behavior. "
        "I will give you a summary of repeated failures or errors the AI made. "
        "Your job: generate a single, concise, actionable rule (1-2 sentences max) "
        "that the AI should follow to avoid this class of mistakes in the future.\n\n"
        "Format: Start with a dash (-) and be specific.\n"
        "If the failures look random with no clear pattern, respond with exactly: SKIP"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Failure patterns:\n{failure_summary}"}
    ]

    settings = database.load_settings()
    provider = settings.get("llm_provider", "deepseek")
    model_name = settings.get("model_name", "deepseek-chat")

    try:
        if provider == "ollama":
            local_model = settings.get("llm_local_model", "qwen3:8b")
            resp = requests.post("http://localhost:11434/api/chat", json={
                "model": local_model, "messages": messages, "stream": False,
                "options": {"temperature": 0.2}
            }, timeout=60)
            if resp.ok:
                return resp.json().get("message", {}).get("content", "").strip()
        else:
            api_key = settings.get(f"{provider}_api_key") or getattr(config, f"{provider.upper()}_API_KEY", "")
            base_urls = {
                "deepseek": "https://api.deepseek.com/chat/completions",
                "openai": "https://api.openai.com/v1/chat/completions",
                "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            }
            url = base_urls.get(provider, base_urls["deepseek"])
            if provider == "deepseek":
                api_key = settings.get("deepseek_api_key") or config.DEEPSEEK_API_KEY

            resp = requests.post(url, headers={
                "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"
            }, json={"model": model_name, "messages": messages, "temperature": 0.2, "max_tokens": 150}, timeout=30)
            if resp.ok:
                return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"[PromptTuner] LLM call failed: {e}")
    return "SKIP"


# ── Core Tuning Cycle ────────────────────────────────────────────────────────

def run_tuning_cycle() -> dict:
    """
    Main entry point. Analyzes recent failures, synthesizes rules,
    and appends them to the agent's learned prompt layer.
    Returns a summary dict with stats.
    """
    failures = get_recent_failures(limit=50)

    if len(failures) < 3:
        return {"status": "skipped", "reason": "Not enough failure data yet.", "rules_total": get_learned_rules_count()}

    # Group failures by tool name
    groups: dict[str, list] = {}
    for f in failures:
        tool = f.get("tool_name", "unknown")
        groups.setdefault(tool, []).append(f.get("result", ""))

    new_rules = []
    for tool_name, results in groups.items():
        if len(results) < 2:
            continue  # Only synthesize from repeated failures

        failure_summary = f"Tool '{tool_name}' failed {len(results)} times.\nSample errors:\n"
        failure_summary += "\n".join(f"  - {r[:200]}" for r in results[:5])

        rule = _call_llm_for_rule(failure_summary)
        if rule and rule.strip().upper() != "SKIP" and rule.startswith("-"):
            new_rules.append(rule.strip())

    if not new_rules:
        return {"status": "no_rules", "reason": "Failures analyzed but no clear patterns found.", "rules_total": get_learned_rules_count()}

    # Append new rules to the persistence file
    existing = load_learned_rules()
    existing_set = set(existing.split("\n"))
    added = [r for r in new_rules if r not in existing_set]

    if not added:
        return {"status": "duplicate", "reason": "Rules already learned.", "rules_total": get_learned_rules_count()}

    timestamp = time.strftime("%Y-%m-%d %H:%M")
    block = f"\n\n# Auto-learned on {timestamp}\n" + "\n".join(added)
    save_learned_rules(existing + block)

    # Auto-commit to git if possible
    _try_git_commit(added)

    return {
        "status": "success",
        "new_rules": added,
        "rules_total": get_learned_rules_count()
    }


def _try_git_commit(rules: list):
    """Commit the improved system prompt to Git."""
    try:
        import subprocess
        root = os.path.dirname(os.path.abspath(LEARNED_PROMPT_FILE))
        msg = f"chore(ai): auto-tune prompt — learned {len(rules)} new rule(s)"
        subprocess.run(["git", "add", "agent_learned_prompt.txt"], cwd=root, capture_output=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=root, capture_output=True)
        print(f"[PromptTuner] Committed learned rules: {msg}")
    except Exception as e:
        print(f"[PromptTuner] Git commit skipped: {e}")


def get_learned_rules_injection() -> str:
    """
    Returns the formatted learned rules block for injection into the
    system prompt at the start of each chat session.
    """
    rules = load_learned_rules()
    if not rules.strip():
        return ""
    return f"\n\n## SELF-LEARNED BEHAVIOR RULES (auto-generated, do not ignore):\n{rules}"
