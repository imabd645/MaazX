"""
Agent tool for Local PC Control.
Allows the agent to simulate media keys (Play/Pause, Volume) and take screenshots using Windows APIs and Pillow.
"""

import os
import ctypes
from datetime import datetime
from core.tool_registry import register_tool

# Virtual-Key Codes for Windows Media Control
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_DOWN = 0x28

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

def _press_key(vk_code):
    """Simulates a hardware key press using user32.dll"""
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

@register_tool
def control_media(action: str) -> str:
    """
    Controls local PC media playback and system volume using Windows Virtual Keys.
    
    Args:
        action: Must be one of: 'play_pause', 'next', 'prev', 'vol_up', 'vol_down', 'mute'.
    """
    action = action.lower()
    mapping = {
        'play_pause': VK_MEDIA_PLAY_PAUSE,
        'next': VK_MEDIA_NEXT_TRACK,
        'prev': VK_MEDIA_PREV_TRACK,
        'vol_up': VK_VOLUME_UP,
        'vol_down': VK_VOLUME_DOWN,
        'mute': VK_VOLUME_MUTE
    }
    
    if action not in mapping:
        return f"Error: Invalid action '{action}'. Valid actions are: {list(mapping.keys())}"
    
    _press_key(mapping[action])
    return f"Successfully sent media key command: {action}"

@register_tool
def take_screenshot(filename: str = None, send_to_whatsapp: str = None) -> str:
    """
    Takes a screenshot of the primary Windows desktop and saves it to the media folder.
    
    Args:
        filename: Optional. The name of the file to save (e.g., 'shot1.png'). If None, an auto-timestamped name is used.
        send_to_whatsapp: Optional. A WhatsApp phone number or ID (e.g., '923350806140' or '923350806140@c.us'). If provided, the screenshot will be sent directly to this contact.
    """
    try:
        from PIL import ImageGrab
    except ImportError:
        return "Error: Python Pillow library is not installed. Run: pip install Pillow"
        
    try:
        # Create media directory if it doesn't exist
        media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
        os.makedirs(media_dir, exist_ok=True)
        
        if not filename:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
        # Ensure it ends in png or jpg
        if not filename.endswith(('.png', '.jpg', '.jpeg')):
            filename += ".png"
            
        filepath = os.path.join(media_dir, filename)
        
        # Grab whole screen
        img = ImageGrab.grab(all_screens=True)
        img.save(filepath)
        
        result_msg = f"Screenshot successfully taken and saved to: {filepath}"
        
        # If requested, forward the image to WhatsApp
        if send_to_whatsapp:
            import requests
            try:
                payload = {
                    "to": send_to_whatsapp,
                    "filePath": filepath,
                    "caption": "Screenshot taken by Agent."
                }
                # Call our new Node.js bridge endpoint
                resp = requests.post("http://localhost:3000/send_media", json=payload, timeout=10)
                if resp.status_code == 200:
                    result_msg += f"\nAnd successfully sent to WhatsApp contact: {send_to_whatsapp}"
                else:
                    result_msg += f"\nFailed to send to WhatsApp. Bridge returned: {resp.text}"
            except Exception as bridge_err:
                result_msg += f"\nFailed to contact WhatsApp bridge: {str(bridge_err)}"
                
        return result_msg
    except Exception as e:
        return f"Error taking screenshot: {str(e)}"

@register_tool
def analyze_screenshot(query: str) -> str:
    """
    Takes a live screenshot of the desktop and passes it to the Gemini Vision AI 
    model to answer a specific question about what is currently on the screen.
    
    Args:
        query: What to look for or analyze on the screen (e.g., "What is the error on the terminal?", "Is Spotify open?")
    """
    try:
        from PIL import ImageGrab
        import google.generativeai as genai
    except ImportError:
        return "Error: Required libraries not found. Ensure Pillow and google-generativeai are installed."
        
    import database as db
    import config
    
    settings = db.load_settings()
    api_key = settings.get("gemini_api_key") or config.GEMINI_API_KEY
    if not api_key:
        return "Error: Gemini API key is missing. Required for Vision capabilities."
        
    try:
        # 1. Grab image in memory
        img = ImageGrab.grab(all_screens=True)
        
        # 2. Configure Gemini
        genai.configure(api_key=api_key)
        
        # Use gemini-1.5-flash for fast multimodal tasks
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 3. Request analysis
        response = model.generate_content([query, img])
        
        return f"Screen Analysis Results:\n\n{response.text}"
    except Exception as e:
        return f"Error during screen analysis: {str(e)}"

@register_tool
def lock_pc() -> str:
    """
    Immediately locks the Windows workstation (same as Win+L).
    """
    try:
        ctypes.windll.user32.LockWorkStation()
        return "Workstation locked successfully."
    except Exception as e:
        return f"Failed to lock workstation: {str(e)}"

@register_tool
def pc_power_control(action: str) -> str:
    """
    Performs power-related actions like shutdown, restart, and sleep.
    
    Args:
        action: Must be one of: 'shutdown', 'restart', 'sleep', 'cancel'.
                'shutdown' and 'restart' include a 60-second grace period.
                'cancel' aborts a pending shutdown/restart.
    """
    import subprocess
    action = action.lower()
    
    try:
        if action == 'shutdown':
            subprocess.run(["shutdown", "/s", "/t", "60"], check=True)
            return "PC is scheduled to shutdown in 60 seconds. Use 'cancel' to abort."
        elif action == 'restart':
            subprocess.run(["shutdown", "/r", "/t", "60"], check=True)
            return "PC is scheduled to restart in 60 seconds. Use 'cancel' to abort."
        elif action == 'sleep':
            # Note: rundll32 powrprof.dll,SetSuspendState 0,1,0 only works if hibernated is disabled
            # or it might hibernate instead.
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
            return "PC is entering sleep/hibernation mode."
        elif action == 'cancel':
            subprocess.run(["shutdown", "/a"], check=True)
            return "Scheduled power action cancelled successfully."
        else:
            return f"Error: Invalid power action '{action}'. Valid: shutdown, restart, sleep, cancel."
    except Exception as e:
        return f"Failed to execute power command: {str(e)}"

@register_tool
def set_pc_volume(level: int) -> str:
    """
    Sets the system volume to a precise percentage (0-100) using PowerShell.
    
    Args:
        level: The volume level to set (0 to 100).
    """
    import subprocess
    if not (0 <= level <= 100):
        return f"Error: Volume level {level} is out of range (0-100)."
    
    try:
        # Convert 0-100 to 0.0-1.0 for the Core Audio API via PowerShell
        volume_float = level / 100.0
        # This PowerShell snippet uses the Audio library to set master volume
        ps_cmd = f"$obj = new-object -com lib.sysaudio.Control; $obj.MasterVolume = {volume_float}"
        # A more standard way without external libs is using NirCmd or simple keypresses, 
        # but since we want PRECISE volume, we use a small script.
        # However, to avoid dependencies, let's use a simpler PowerShell method:
        ps_script = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})" # This is for brightness
        # For Volume, let's use the standard SndVol way or similar.
        # Actually, let's use this reliable PowerShell approach for Volume:
        ps_cmd = f"(new-object -com shell.application).NameSpace(0).ParseName('C:').InvokeVerb('Properties'); (New-Object -ComObject WScript.Shell).SendKeys([char]175*50); (New-Object -ComObject WScript.Shell).SendKeys([char]174*{100-level})"
        # That's messy. Let's use the absolute best one for Windows:
        ps_cmd = f"$w = New-Object -ComObject WScript.Shell; for($i=0; $i -lt 50; $i++) {{ $w.SendKeys([char]174) }}; for($i=0; $i -lt {level // 2}; $i++) {{ $w.SendKeys([char]175) }}"
        
        subprocess.run(["powershell", "-Command", ps_cmd], check=True)
        return f"Volume set to approximately {level}%."
    except Exception as e:
        return f"Failed to set volume: {str(e)}"

@register_tool
def launch_app(app_name: str) -> str:
    """
    Launches a Windows application by name or common path.
    
    Args:
        app_name: The name of the app (e.g., 'notepad', 'calc', 'chrome', 'spotify').
    """
    import subprocess
    app_name = app_name.lower().strip()
    
    # Common mappings
    apps = {
        "chrome": "chrome.exe",
        "spotify": "spotify.exe",
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "code": "code",
        "calculator": "calc.exe"
    }
    
    target = apps.get(app_name, app_name)
    
    try:
        # Try launching via shell (works for registered aliases)
        subprocess.Popen(target, shell=True)
        return f"Attempting to launch '{app_name}'..."
    except Exception as e:
        return f"Failed to launch '{app_name}': {str(e)}"

@register_tool
def close_app(app_name: str) -> str:
    """
    Closes a running application by its process name.
    
    Args:
        app_name: The name of the process to close (e.g., 'notepad', 'chrome', 'spotify').
    """
    import psutil
    app_name = app_name.lower().strip()
    if not app_name.endswith('.exe') and app_name not in ['code']: # code is usually scripts
        app_name += '.exe'
        
    closed_count = 0
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and proc.info['name'].lower() == app_name:
                proc.terminate()
                closed_count += 1
        
        if closed_count > 0:
            return f"Successfully closed {closed_count} instance(s) of '{app_name}'."
        else:
            return f"No running process found named '{app_name}'."
    except Exception as e:
        return f"Error trying to close '{app_name}': {str(e)}"

@register_tool
def spotify_search(query: str) -> str:
    """
    Opens the Spotify Desktop app and searches for a specific song, artist, or album.
    Note: On Windows, this uses the 'spotify:search' URI scheme.
    
    Args:
        query: The song name, artist, or search term (e.g., 'Starboy', 'The Weeknd', '80s Rock').
    """
    import subprocess
    import urllib.parse
    import time
    
    try:
        # Encode the query for URI
        encoded_query = urllib.parse.quote(query)
        # Windows command to start a URI
        uri = f"spotify:search:{encoded_query}"
        
        # Using shell=True for 'start' command on Windows
        subprocess.Popen(["start", uri], shell=True)
        
        # Wait for Spotify to load results (3 seconds for stability)
        time.sleep(3)
        
        # Exact sequence provided by user to trigger play:
        _press_key(VK_TAB)    # Shift focus from search bar
        time.sleep(0.5)
        _press_key(VK_DOWN)   # Select the top result
        time.sleep(0.5)
        _press_key(VK_RETURN) # Trigger play (1st enter)
        time.sleep(0.5)
        _press_key(VK_RETURN) # Confirm play (2nd enter)
        
        return f"Spotify search for '{query}' performed and play sequence executed (Tab -> Down -> Enter x2)."
    except Exception as e:
        return f"Failed to perform detailed Spotify search and play sequence: {str(e)}"
