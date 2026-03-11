
import sqlite3
import os

DB_PATH = os.path.join(os.getcwd(), "agent_data.db")

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(whatsapp_messages)")
    cols = [row[1] for row in cursor.fetchall()]
    
    new_cols = [
        ("tool_calls", "TEXT DEFAULT '[]'"),
        ("tool_call_id", "TEXT"),
        ("name", "TEXT")
    ]
    
    for col_name, col_def in new_cols:
        if col_name not in cols:
            print(f"Adding column {col_name} to whatsapp_messages...")
            cursor.execute(f"ALTER TABLE whatsapp_messages ADD COLUMN {col_name} {col_def}")
        else:
            print(f"Column {col_name} already exists.")
            
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
