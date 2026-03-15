import sqlite3
import os

db_path = "agent_data.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- ANALYZING MEMORIES ---")
cursor.execute("SELECT * FROM memories WHERE key LIKE '%abdullah%' OR value LIKE '%global%' OR value LIKE '%instruction%';")
rows = cursor.fetchall()
for row in rows:
    print(f"Key: {row['key']} | Value: {row['value']}")

print("\n--- ANALYZING RECENT WHATSAPP HISTORY ---")
cursor.execute("SELECT * FROM wa_history ORDER BY id DESC LIMIT 5;")
rows = cursor.fetchall()
for row in rows:
    print(f"Role: {row['role']} | Content: {row['content'][:100]}...")

conn.close()
