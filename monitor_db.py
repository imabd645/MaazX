import sqlite3
import os
import time

db_path = "f:/AI Agnet/agent_data.db"
os.environ['SQLITE_LIMIT_VARIABLE_NUMBER'] = '999'

def check():
    if not os.path.exists(db_path):
        print("DB not found")
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    if 'apscheduler_jobs' in tables:
        cur.execute("SELECT id, next_run_time FROM apscheduler_jobs")
        jobs = cur.fetchall()
        print(f"Jobs: {jobs}")
    else:
        print("No apscheduler_jobs table")
    conn.close()

if __name__ == "__main__":
    check()
