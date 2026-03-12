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
    print(f"\n[Scheduler] WAKING UP TO EXECUTE TASK: {prompt}")
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
    
    # SAFETY CHECK: If next_run_time is way in the future (e.g. > 1 week), it's likely a cron mismatch
    import datetime
    if job.next_run_time:
        now = datetime.datetime.now(job.next_run_time.tzinfo)
        diff = job.next_run_time - now
        if diff.days > 7:
            # Delete the job and return error
            err_msg = f"Error: Task scheduled for {job.next_run_time} ({diff.days} days away). This is too far in the future. Check if you used the correct day-of-week (0=Mon) or use 'schedule_once' with a specific date."
            scheduler.remove_job(job.id)
            return err_msg
    
    return str(job.id)

def add_date_job(prompt: str, run_at: str, description: str = "One-time Task") -> str:
    """
    Registers a one-time job using a specific date/time string.
    Supported format: YYYY-MM-DD HH:MM:SS
    """
    from apscheduler.triggers.date import DateTrigger
    import datetime
    
    # Try parsing common formats
    try:
        dt = datetime.datetime.fromisoformat(run_at.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.datetime.strptime(run_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return f"Error: Invalid date format '{run_at}'. Use YYYY-MM-DD HH:MM:SS"

    job = scheduler.add_job(
        execute_scheduled_task,
        trigger=DateTrigger(run_date=dt),
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
