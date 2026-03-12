"""
Agent tool for System Monitoring and Process Management.
Uses the psutil library to collect stats and manage local processes.
"""

import psutil
import os
from core.tool_registry import register_tool

@register_tool
def get_system_stats() -> str:
    """
    Retrieves real-time system health statistics including CPU, RAM, and Disk usage.
    """
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        stats = [
            f"📊 **System Health Report**",
            f"- **CPU Usage**: {cpu_usage}%",
            f"- **RAM Usage**: {ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)",
            f"- **Disk Usage**: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)"
        ]
        
        return "\n".join(stats)
    except Exception as e:
        return f"Error retrieving system stats: {str(e)}"

@register_tool
def list_processes(filter_name: str = None) -> str:
    """
    Lists all active processes running on the host machine.
    
    Args:
        filter_name: Optional. Case-insensitive string to filter process names by (e.g., 'python', 'chrome').
    """
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                pinfo = proc.info
                name = pinfo['name']
                pid = pinfo['pid']
                mem = pinfo['memory_info'].rss // (1024**2) # MB
                
                if not filter_name or filter_name.lower() in name.lower():
                    processes.append(f"PID: {pid} | Name: {name} | Mem: {mem}MB")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if not processes:
            return f"No processes found{' matching \"' + filter_name + '\"' if filter_name else ''}."
            
        # Limit output to top 30 to avoid overwhelming the LLM
        output = "\n".join(processes[:30])
        if len(processes) > 30:
            output += f"\n...and {len(processes) - 30} more (use a more specific filter)."
            
        return f"Active Processes:\n{output}"
    except Exception as e:
        return f"Error listing processes: {str(e)}"

@register_tool
def kill_process(target: str) -> str:
    """
    Terminates a process by its PID or its exact Name.
    
    Args:
        target: The numeric PID (as a string) or the name of the process (e.g., 'notepad.exe').
    """
    try:
        if target.isdigit():
            # Kill by PID
            pid = int(target)
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            return f"Successfully terminated process '{name}' (PID: {pid})."
        else:
            # Kill by Name (all instances)
            count = 0
            for proc in psutil.process_iter(['name']):
                if proc.info['name'].lower() == target.lower():
                    proc.terminate()
                    count += 1
            
            if count > 0:
                return f"Successfully terminated {count} instance(s) of '{target}'."
            else:
                return f"No processes found with the name '{target}'."
                
    except psutil.NoSuchProcess:
        return f"Error: Process '{target}' not found."
    except psutil.AccessDenied:
        return f"Error: Permission denied when trying to kill '{target}'."
    except Exception as e:
        return f"Error killing process: {str(e)}"
