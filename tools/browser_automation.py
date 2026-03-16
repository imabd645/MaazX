"""
Playwright Browser Automation Tool.
Allows the agent to perform advanced web interactions beyond simple search/read.
"""

import os
import time
import asyncio
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright
from core.tool_registry import register_tool

# Removed globals for thread safety
# Browser lifecycle is now handled locally within browser_automate

@register_tool
def browser_automate(actions: List[Dict[str, Any]]) -> str:
    """
    Executes a sequence of browser actions (navigate, click, type, wait).
    
    Args:
        actions: A list of action dictionaries. Supported actions:
            - {"type": "navigate", "url": "..."}
            - {"type": "click", "selector": "..."}
            - {"type": "type", "selector": "...", "text": "..."}
            - {"type": "wait", "ms": 1000}
            - {"type": "screenshot", "send_to_whatsapp": "phone_number"}
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            output = []
            for action in actions:
                a_type = action.get("type")
                
                if a_type == "navigate":
                    url = action.get("url")
                    page.goto(url, wait_until="networkidle")
                    output.append(f"Navigated to {url}")
                    
                elif a_type == "click":
                    selector = action.get("selector")
                    page.click(selector)
                    output.append(f"Clicked {selector}")
                    
                elif a_type == "type":
                    selector = action.get("selector")
                    text = action.get("text")
                    page.fill(selector, text)
                    output.append(f"Typed '{text}' into {selector}")
                    
                elif a_type == "wait":
                    ms = action.get("ms", 1000)
                    page.wait_for_timeout(ms)
                    output.append(f"Waited for {ms}ms")
                    
                elif a_type == "screenshot":
                    wa_phone = action.get("send_to_whatsapp")
                    screenshot_path = os.path.abspath("browser_capture.png")
                    page.screenshot(path=screenshot_path, full_page=False)
                    output.append(f"Captured screenshot to {screenshot_path}")
                    
                    if wa_phone:
                        # Import here to avoid circular dependencies
                        import requests
                        payload = {
                            "to": wa_phone,
                            "filePath": screenshot_path,
                            "caption": f"Browser Screenshot: {page.title()}"
                        }
                        try:
                            resp = requests.post("http://localhost:3000/send_media", json=payload, timeout=20)
                            if resp.status_code == 200:
                                output.append(f"Sent screenshot to {wa_phone}")
                            else:
                                output.append(f"Failed to send to WhatsApp: {resp.text}")
                        except Exception as e:
                            output.append(f"WhatsApp forward error: {str(e)}")
            
            browser.close()
            return "\n".join(output) if output else "No actions performed."
            
    except Exception as e:
        return f"Browser Error: {str(e)}"

@register_tool
def browser_screenshot(send_to_whatsapp: Optional[str] = None) -> str:
    """
    Takes a screenshot of the current browser page.
    """
    return browser_automate([{"type": "screenshot", "send_to_whatsapp": send_to_whatsapp}])
