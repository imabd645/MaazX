"""Tool: schedule_action — schedule an autonomous AI task for the future."""

import re
from core.tool_registry import register_tool
from core.scheduler import add_cron_job

@register_tool
def schedule_action(prompt: str, cron_expression: str, description: str) -> str:
    """Schedules an autonomous future task using a standard cron expression.
    The agent will wake up in the background at the specified cron interval, read the prompt, and execute the task (e.g., scraping the web, sending a WhatsApp message).
    
    Args:
        prompt: The exact query or instruction the future agent should execute when it wakes up. E.g., 'Check Apple stock price and WhatsApp it to Maaz.'
        cron_expression: A standard 5-part cron string representing when to run.
            Format: minute hour day month day_of_week
            Examples:
            '0 8 * * *' = Every day at 8:00 AM
            '*/5 * * * *' = Every 5 minutes
            '30 14 * * 1-5' = 2:30 PM, Mon-Fri
        description: A human-readable description of the job (e.g., 'Daily Morning News Summary').
    """
    
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        return "Error: Internal cron format error. Please pass exactly 5 elements separated by spaces (minute hour day month day_of_week)."
    
    minute, hour, day, month, day_of_week = parts
    
    try:
        job_id = add_cron_job(
            prompt=prompt,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            description=description
        )
        return f"Successfully scheduled task '{description}'. Job ID: {job_id}\nCron: {cron_expression}\nPrompt: {prompt}"
    except Exception as e:
        return f"Failed to schedule task: {str(e)}"
