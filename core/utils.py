import re

def strip_markdown(text):
    """
    Removes common markdown formatting like bold (**), italics (* or _), 
    and blockquotes (>) to make text suitable for plain-text systems.
    """
    if not text:
        return ""
    # Remove bold/italics
    text = re.sub(r'(\*\*|__|[\*_])', '', text)
    # Remove horizontal rules
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Remove blockquotes
    text = re.sub(r'^\s*>\s*', '', text, flags=re.MULTILINE)
    # Remove links [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # Remove code blocks and inline code
    text = re.sub(r'`{1,3}.*?`{1,3}', '', text, flags=re.DOTALL)
    
    return text.strip()
