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
