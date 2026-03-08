"""
Background Scheduler for the AI Agent.
Handles executing delayed or recurring tasks (e.g. cron jobs) autonomously.
"""
import os
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

# Ensure we use an absolute path for the DB so the scheduler finds it regardless of cwd
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_data.db"))

jobstores = {
    'default': SQLAlchemyJobStore(url=f'sqlite:///{DB_PATH}')
}

scheduler = BackgroundScheduler(jobstores=jobstores)

def execute_scheduled_task(prompt: str):
    """
    The function that runs when a cron job fires.
    It spawns a fresh AI Agent instance and gives it the prompt.
    """
    print(f"\n[Scheduler] ⏰ WAKING UP TO EXECUTE TASK: {prompt}")
    try:
        # Import lazily to avoid circular imports during boot
        from core.agent import Agent
        agent = Agent()
        reply = agent.send(prompt)
        print(f"[Scheduler] ✅ Task completed successfully.\nAgent reply: {reply}")
    except Exception as e:
        print(f"[Scheduler] ❌ Task failed with error: {e}")

def start_scheduler():
    """Boots the APScheduler in the background loop."""
    if not scheduler.running:
        scheduler.start()
        print(f"[Scheduler] Background Cron Engine Started. (Jobs store: {DB_PATH})")

def add_cron_job(prompt: str, minute: str = "*", hour: str = "*", day: str = "*", month: str = "*", day_of_week: str = "*", description: str = "Scheduled Task") -> str:
    """
    Registers a new cron job in the database.
    
    Returns the job ID.
    """
    trigger = CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week
    )
    
    # We pass the prompt into the executor function
    job = scheduler.add_job(
        execute_scheduled_task, 
        trigger=trigger, 
        args=[prompt],
        name=description[:50]
    )
    
    return str(job.id)

def get_all_jobs() -> list:
    """Returns a list of all currently scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else "Paused",
            "prompt": job.args[0] if job.args else ""
        })
    return jobs

def remove_job(job_id: str) -> bool:
    """Removes a job by ID. Returns True if successful, False otherwise."""
    try:
        scheduler.remove_job(job_id)
        return True
    except Exception as e:
        print(f"[Scheduler] Failed to remove job {job_id}: {e}")
        return False
