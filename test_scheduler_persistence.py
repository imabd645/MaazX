import sys
import os

# Add the project root to sys.path
sys.path.append('f:/AI Agnet')

from core.scheduler import add_date_job, start_scheduler
import time
import datetime

def test_schedule():
    start_scheduler()
    # Schedule for 1 hour from now to ensure it stays in DB
    run_at = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Scheduling for: {run_at}")
    job_id = add_date_job("Test prompt", run_at, "Test Job persistence")
    print(f"Job ID: {job_id}")
    
    # Wait a bit for persistence
    time.sleep(2)
    
    # Check DB
    import sqlite3
    conn = sqlite3.connect('f:/AI Agnet/agent_data.db')
    cur = conn.cursor()
    cur.execute("SELECT id, next_run_time FROM apscheduler_jobs")
    print(f"Jobs in DB after adding: {cur.fetchall()}")
    conn.close()

if __name__ == "__main__":
    test_schedule()
