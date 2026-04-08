import os
import uuid
import tempfile
from core.tool_registry import register_tool

@register_tool
def generate_pdf(html_content: str, output_path: str = None) -> str:
    \"\"\"
    Generates a beautifully styled PDF from HTML content using Playwright.
    HTML should contain embedded CSS within <style> tags for styling.
    If no output_path is provided, a reasonably named random PDF is generated.
    Returns the absolute path to the generated PDF.
    
    Args:
        html_content (str): The full HTML string to render, including inline CSS.
        output_path (str, optional): The destination file path ending in .pdf. 
                                     If omitted, a random filename is generated in the 'exports' folder.
    \"\"\"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "Error: Playwright library is not installed. Please run `pip install playwright`."
        
    if not output_path:
        base_dir = os.path.join(os.getcwd(), "exports")
        os.makedirs(base_dir, exist_ok=True)
        filename = f"document_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(base_dir, filename)
        
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Use set_content to process raw HTML strings instantly
            page.set_content(html_content, wait_until="networkidle")
            
            # Print to PDF with full fidelity and CSS backgrounds
            page.pdf(
                path=output_path, 
                format="A4",
                print_background=True,
                margin={"top": "20px", "right": "20px", "bottom": "20px", "left": "20px"}
            )
            browser.close()
            
        return f"Successfully generated beautifully styled PDF at: {output_path}"
        
    except Exception as e:
        if "Executable doesn't exist" in str(e).lower() or "playwright install" in str(e).lower():
            return "Error: Playwright browsers are not installed. You configure it by running `playwright install chromium` in your CLI."
        return f"Error generating PDF: {str(e)}"
