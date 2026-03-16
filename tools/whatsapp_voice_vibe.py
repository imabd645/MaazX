"""
Tools for WhatsApp voice notes (PTT) and emoji reactions.
"""

import os
import requests
import time
from gtts import gTTS
from core.tool_registry import register_tool

BRIDGE_URL = "http://127.0.0.1:3000"

@register_tool
def wa_react_to_message(message_id: str, emoji: str) -> str:
    """
    Reacts to a specific WhatsApp message with an emoji.
    
    Args:
        message_id: The WhatsApp message ID (e.g. 'false_923123456789@c.us_ABC123').
        emoji: The emoji character to react with (e.g. '👍', '❤️', '😂').
    """
    try:
        res = requests.post(
            f"{BRIDGE_URL}/react",
            json={"messageId": message_id, "emoji": emoji},
            timeout=15
        )
        res.raise_for_status()
        return f"Success! Reacted with {emoji} to message {message_id}."
    except Exception as e:
        return f"Error reacting to message: {str(e)}"

@register_tool
def wa_send_voice_note(to: str, text: str) -> str:
    """
    Converts text to speech and sends it as a native WhatsApp voice note (PTT).
    
    Args:
        to: The recipient's WhatsApp ID (e.g. '923123456789@c.us').
        text: The message content to be spoken in the voice note.
    """
    try:
        # 1. Create media directory if it doesn't exist
        media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
        os.makedirs(media_dir, exist_ok=True)
        
        filename = f"vn_{int(time.time())}.mp3"
        filepath = os.path.join(media_dir, filename)
        
        # 2. Generate speech
        print(f"Generating voice note: '{text}'...")
        tts = gTTS(text=text, lang='en')
        tts.save(filepath)
        
        # 3. Send via bridge with isPtt=True
        payload = {
            "to": to,
            "filePath": os.path.abspath(filepath),
            "isPtt": True
        }
        
        res = requests.post(
            f"{BRIDGE_URL}/send_media",
            json=payload,
            timeout=30
        )
        res.raise_for_status()
        
        return f"Success! Voice note sent to {to}."
    except Exception as e:
        return f"Error sending voice note: {str(e)}"
