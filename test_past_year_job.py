import sys
import os

# Add the project root to sys.path
sys.path.append('f:/AI Agnet')

from core.scheduler import add_date_job, start_scheduler
import time
import datetime

def test_past_year():
    start_scheduler()
    # Schedule for a past date (2025)
    run_at = "2025-03-15 17:34:00"
    print(f"Scheduling for PAST DATE: {run_at}")
    try:
        job_id = add_date_job("Past year test prompt", run_at, "Past Year persistence test")
        print(f"Job ID: {job_id}")
    except Exception as e:
        print(f"Caught error adding past job: {e}")
    
    # Wait a bit
    time.sleep(2)
    
    # Check DB
    import sqlite3
    conn = sqlite3.connect('f:/AI Agnet/agent_data.db')
    cur = conn.cursor()
    cur.execute("SELECT id, next_run_time FROM apscheduler_jobs")
    print(f"Jobs in DB after adding past year job: {cur.fetchall()}")
    conn.close()

if __name__ == "__main__":
    test_past_year()
