"""
Agent tool for Webcam Control.
Allows the agent to capture photos from the PC's webcam and send them to WhatsApp.
"""

import os
import cv2
import time
from datetime import datetime
from core.tool_registry import register_tool

@register_tool
def take_webcam_photo(send_to_whatsapp: str = None) -> str:
    """
    Captures a photo from the default PC webcam and saves it to the media folder.
    
    Args:
        send_to_whatsapp: Optional. A WhatsApp phone number or ID (e.g., '923350806140'). If provided, the photo will be sent directly to this contact.
    """
    try:
        # Create media directory if it doesn't exist
        media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
        os.makedirs(media_dir, exist_ok=True)
        
        filename = f"webcam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(media_dir, filename)
        
        # 1. Initialize camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Error: Could not open webcam. Ensure it is connected and not in use by another app."
            
        # 2. Warm up the camera (important for exposure/focus)
        # We discard the first few frames to allow auto-exposure to adjust
        time.sleep(2)
        for _ in range(10):
            cap.read()
        
        # 3. Capture final frame
        ret, frame = cap.read()
        
        # 4. Release immediately
        cap.release()
        
        if not ret:
            return "Error: Could not read frame from webcam."
            
        # 5. Save the image
        cv2.imwrite(filepath, frame)
        
        result_msg = f"Webcam photo successfully taken and saved to: {filepath}"
        
        # 6. Forward to WhatsApp if requested
        if send_to_whatsapp:
            import requests
            try:
                payload = {
                    "to": send_to_whatsapp,
                    "filePath": filepath,
                    "caption": f"Webcam snapshot captured at {datetime.now().strftime('%H:%M:%S')}."
                }
                # Call our Node.js bridge endpoint
                resp = requests.post("http://localhost:3000/send_media", json=payload, timeout=15)
                if resp.status_code == 200:
                    result_msg += f"\nAnd successfully sent to WhatsApp contact: {send_to_whatsapp}"
                else:
                    result_msg += f"\nFailed to send to WhatsApp. Bridge returned: {resp.text}"
            except Exception as bridge_err:
                result_msg += f"\nFailed to contact WhatsApp bridge: {str(bridge_err)}"
                
        return result_msg
        
    except Exception as e:
        return f"Error taking webcam photo: {str(e)}"
