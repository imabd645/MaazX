"""
LinkedIn Management Tool — Browser-based.
Allows the agent to post updates to LinkedIn by automating the browser.
"""

import os
import time
from typing import List, Dict, Any, Optional
from core.tool_registry import register_tool
from tools.browser_automation import browser_automate

@register_tool
def post_to_linkedin(content: str) -> str:
    """
    Posts content to LinkedIn using browser automation.
    Assumes the user is already logged in to LinkedIn in the internal browser session.
    """
    try:
        # Step 1: Navigate to LinkedIn Home
        nav_res = browser_automate([{"type": "navigate", "url": "https://www.linkedin.com/feed/"}])
        if "Error" in nav_res:
             return nav_res

        # Step 2: Check if logged in (look for the "Start a post" button)
        # We'll use a wait to ensure the feed is loaded
        time.sleep(3)
        
        # Action sequence:
        # 1. Click the "Start a post" button
        # 2. Fill the content
        # 3. Click "Post"
        
        # Note: LinkedIn selectors are notoriously dynamic, but we can try common ones.
        # Button to open the post modal: ".share-box-feed-entry__trigger" or similar
        
        actions = [
            {"type": "click", "selector": "button.share-box-feed-entry__trigger"},
            {"type": "wait", "ms": 2000},
            {"type": "type", "selector": ".editor-content div[role='textbox']", "text": content},
            {"type": "wait", "ms": 1000},
            {"type": "click", "selector": "button.share-actions__primary-action"},
            {"type": "wait", "ms": 3000},
            {"type": "screenshot", "send_to_whatsapp": None} # Capture for verification
        ]
        
        res = browser_automate(actions)
        if "Error" in res:
            return f"Posting failed. You might need to log in first. Captured a screenshot to browser_capture.png.\n{res}"
            
        return f"Successfully attempted to post to LinkedIn. Verification screenshot saved.\nDetails:\n{res}"

    except Exception as e:
        return f"LinkedIn Posting Error: {str(e)}"

@register_tool
def draft_linkedin_update() -> str:
    """
    Analyzes recent project changes and drafts a professional LinkedIn post update.
    Returns the suggested markdown text.
    """
    try:
        # Import git manager lazily
        from tools.git_manager import get_git_diff
        diff = get_git_diff()
        
        # If no diff, just return a generic template
        if not diff or "Error" in diff:
            return "I couldn't find any recent code changes. Please provide a manual topic or update some files first!"
            
        # We return the diff summary and let the LLM handle the creative writing in the 'send' loop
        return f"Recent Development Context Found:\n{diff}\n\nPlease use this context to craft a premium LinkedIn post."
        
    except Exception as e:
        return f"Error drafting update: {str(e)}"

if __name__ == "__main__":
    # Test draft
    print(draft_linkedin_update())
