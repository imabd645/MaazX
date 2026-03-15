import sqlite3

db_path = "agent_data.db"
conn = sqlite3.connect(db_path)

# Update the main response memory
conn.execute("""
    UPDATE memories 
    SET value = 'I was created by Abdullah Masood, a software engineer and AI developer from Pakistan.' 
    WHERE key = 'abdullah_masood_response'
""")

# Delete any memories that are just meta-instructions about "global instructions"
conn.execute("DELETE FROM memories WHERE value LIKE '%global instructions%'")

conn.commit()
conn.close()
print("Memories sanitized successfully.")
