import requests
from bs4 import BeautifulSoup
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

def search_web(query: str, max_results: int = 5) -> str:
    """
    Searches the web and returns the top results.
    Useful for finding documentation, tutorials, or answering questions.
    
    Args:
        query: The search term or question.
        max_results: The maximum number of results to return (default 5).
        
    Returns:
        A formatted string with search results (Title, Snippet, URL).
    """
    if DDGS is None:
        return "Error: duckduckgo-search package is not installed. Run 'pip install duckduckgo-search'."
        
    try:
        results = ""
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=max_results)):
                results += f"[{i+1}] {r.get('title', '')}\n"
                results += f"URL: {r.get('href', '')}\n"
                results += f"Snippet: {r.get('body', '')}\n\n"
        
        if not results:
            return f"No results found for query: {query}"
        return results.strip()
    except Exception as e:
        return f"Error performing web search: {str(e)}"

def read_webpage(url: str) -> str:
    """
    Fetches a webpage and extracts its main text content.
    Useful for reading documentation, articles, or GitHub repos discovered via search.
    
    Args:
        url: The full URL of the webpage to read.
        
    Returns:
        The extracted text context of the page, up to 10000 characters.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove noisy elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
            script.extract()
            
        # Get raw text with some basic formatting
        text = soup.get_text(separator=' ', strip=True)
        
        # Collapse multiple spaces
        import re
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Return truncated to avoid breaking token limits
        max_len = 10000
        if len(text) > max_len:
            return text[:max_len] + "\n...[CONTENT TRUNCATED]..."
        return text
    except Exception as e:
        return f"Error reading webpage {url}: {str(e)}"
