"""
Agent tool for semantic codebase search using RAG (Retrieval-Augmented Generation).
Returns matched code snippets from ChromaDB based on embedding similarity.
"""

from core.tool_registry import register_tool
from core import indexer


@register_tool
def semantic_search(query: str, max_results: int = 5) -> str:
    """
    Search the codebase for code or text that matches the *meaning* of the query.
    Use this when you don't know exactly what file to look in, but you know what it conceptually does 
    (e.g. 'Where is the chat API endpoint?', 'How are database settings saved?').

    Args:
        query: A natural language sentence or code concept to search for.
        max_results: The number of code snippets to return (default 5).

    Returns:
        A string containing the most relevant code snippets and their filepaths.
    """
    try:
        matches = indexer.semantic_search(query, n_results=max_results)
        
        if isinstance(matches, str):
            return f"Error during search: {matches}"
            
        if not matches:
            return "No semantic matches found. Did the user index the codebase?"

        response = f"Found {len(matches)} semantic matches:\n\n"
        for i, match in enumerate(matches):
            response += f"--- Match {i+1} from {match['filepath']} ---\n"
            response += f"{match['content']}\n\n"
            
        return response

    except Exception as e:
        return f"Error searching vector database: {e}"
