"""
Bridge Manager — handles the lifecycle of the Node.js WhatsApp bridge.
Spawns index.js as a subprocess and ensures it is cleaned up on exit.
"""

import os
import subprocess
import threading
import time
import atexit
import signal

# Track the process globally
_bridge_process = None

def start_bridge():
    """
    Spawns the Node.js bridge in a separate process.
    This should be called when the main Python app starts.
    """
    global _bridge_process
    
    if _bridge_process is not None:
        return # Already running
        
    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bridge_dir = os.path.join(base_dir, "whatsapp_bridge")
    bridge_script = os.path.join(bridge_dir, "index.js")
    
    if not os.path.exists(bridge_script):
        print(f"[Bridge Manager] Error: Bridge script not found at {bridge_script}")
        return

    def run():
        global _bridge_process
        print(f"[Bridge Manager] Starting WhatsApp Bridge in {bridge_dir}...")
        
        try:
            # We use 'node' command. Node must be in PATH.
            _bridge_process = subprocess.Popen(
                ["node", "index.js"],
                cwd=bridge_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True # For Windows
            )
            
            # Monitor output in background to see logs in console if needed
            for line in _bridge_process.stdout:
                if line:
                    print(f"[Bridge Out] {line.strip()}")
                    
        except Exception as e:
            print(f"[Bridge Manager] Failed to start Node bridge: {e}")
            _bridge_process = None

    # Run in a daemon thread so it doesn't block the UI
    t = threading.Thread(target=run, daemon=True)
    t.start()
    
    # Give it a second to initialize
    time.sleep(1)
    
    # Register shutdown hook
    atexit.register(stop_bridge)

def stop_bridge():
    """
    Terminates the Node.js bridge process.
    """
    global _bridge_process
    if _bridge_process:
        print("[Bridge Manager] Stopping WhatsApp Bridge...")
        try:
            # On Windows, taskkill is often safer for shell=True processes
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(_bridge_process.pid)], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _bridge_process.terminate()
            _bridge_process = None
            print("[Bridge Manager] Process terminated.")
        except Exception as e:
            print(f"[Bridge Manager] Error stopping bridge: {e}")
