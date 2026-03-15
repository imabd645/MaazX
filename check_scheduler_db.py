import sqlite3
import os

db_path = "f:/AI Agnet/agent_data.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print(f"Tables: {tables}")
    
    # Check jobs if table exists
    if ('apscheduler_jobs',) in tables:
        cur.execute("SELECT id, next_run_time FROM apscheduler_jobs")
        jobs = cur.fetchall()
        print(f"Jobs in apscheduler_jobs: {jobs}")
    else:
        print("Table 'apscheduler_jobs' not found.")
        
    conn.close()
else:
    print(f"Database not found at {db_path}")
