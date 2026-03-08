"""
SQLite storage for settings and chat history.
Database file: agent_data.db in the project root.
"""

import sqlite3
import json
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_data.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            session   TEXT NOT NULL,
            role      TEXT NOT NULL,
            content   TEXT NOT NULL,
            tool_calls TEXT DEFAULT '[]',
            timestamp REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS terminal_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            command   TEXT NOT NULL,
            output    TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            cwd       TEXT NOT NULL,
            timestamp REAL NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS whatsapp_contacts (
            phone_number TEXT PRIMARY KEY,
            name         TEXT,
            summary      TEXT DEFAULT '',
            rules        TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT NOT NULL,
            role         TEXT NOT NULL,
            content      TEXT NOT NULL,
            timestamp    REAL NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# ── Settings ────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "auto_run_commands": True,
    "model_name": "gemini-2.5-flash",
    "command_timeout": 60,
    "max_dir_depth": 3,
    "tool_mode": "any",
    "theme": "dark",
    "openrouter_api_key": "",
    "wa_owner_name": "User",
}


def load_settings():
    """Load all settings from DB, merged with defaults."""
    conn = _get_conn()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()

    saved = {}
    for row in rows:
        try:
            saved[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            saved[row["key"]] = row["value"]

    merged = {**DEFAULT_SETTINGS, **saved}
    return merged


def save_settings(settings: dict):
    """Save settings dict to DB."""
    conn = _get_conn()
    for key, value in settings.items():
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
    conn.commit()
    conn.close()


# ── Chat History ────────────────────────────────────────────
def save_chat_message(session: str, role: str, content: str, tool_calls: list = None):
    """Save a single chat message."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO chat_history (session, role, content, tool_calls, timestamp) VALUES (?, ?, ?, ?, ?)",
        (session, role, content, json.dumps(tool_calls or []), time.time()),
    )
    conn.commit()
    conn.close()


def get_chat_sessions():
    """Return list of unique sessions with their latest timestamp."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT session, MAX(timestamp) as last_ts, COUNT(*) as msg_count
        FROM chat_history
        GROUP BY session
        ORDER BY last_ts DESC
        LIMIT 50
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_chat_history(session: str, limit: int = 100):
    """Return messages for a given session."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, tool_calls, timestamp FROM chat_history WHERE session = ? ORDER BY id ASC LIMIT ?",
        (session, limit),
    ).fetchall()
    conn.close()
    return [
        {
            "role": row["role"],
            "content": row["content"],
            "tool_calls": json.loads(row["tool_calls"]),
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]


def delete_chat_session(session: str):
    """Delete all messages in a session."""
    conn = _get_conn()
    conn.execute("DELETE FROM chat_history WHERE session = ?", (session,))
    conn.commit()
    conn.close()


# ── Terminal History ────────────────────────────────────────
def save_terminal_entry(command: str, output: str, exit_code: int, cwd: str):
    """Save a terminal command + output."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO terminal_history (command, output, exit_code, cwd, timestamp) VALUES (?, ?, ?, ?, ?)",
        (command, output, exit_code, cwd, time.time()),
    )
    conn.commit()
    conn.close()


def get_terminal_history(limit: int = 50):
    """Return recent terminal history."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT command, output, exit_code, cwd, timestamp FROM terminal_history ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]


# ── WhatsApp Agent ────────────────────────────────────────────

def get_wa_contact(phone_number: str) -> dict:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM whatsapp_contacts WHERE phone_number = ?", (phone_number,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_wa_contacts():
    conn = _get_conn()
    rows = conn.execute("SELECT phone_number, name, summary, rules FROM whatsapp_contacts ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_wa_contact(phone_number: str, name: str, summary: str = "", rules: str = ""):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO whatsapp_contacts (phone_number, name, summary, rules) VALUES (?, ?, ?, ?)",
        (phone_number, name, summary, rules)
    )
    conn.commit()
    conn.close()

def save_wa_message(phone_number: str, role: str, content: str):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO whatsapp_messages (phone_number, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (phone_number, role, content, time.time())
    )
    conn.commit()
    conn.close()

def get_wa_history(phone_number: str, limit: int = 40):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, timestamp FROM whatsapp_messages WHERE phone_number = ? ORDER BY id ASC LIMIT ?",
        (phone_number, limit)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Initialize DB on import
init_db()
