"""
Agent tool to query the Knowledge Base RAG collection.
Allows the AI to find answers within uploaded PDFs, Word Docs, and text files.
"""

from core.tool_registry import register_tool
from core import knowledge_indexer

@register_tool
def query_knowledge(query: str, max_results: int = 5) -> str:
    """
    Search the Knowledge Base for context that matches the *meaning* of the query.
    Use this when the user asks questions about uploaded documents (like 'What does the PDF say about X?' 
    or 'Summarize the company policy').

    Args:
        query: A natural language sentence to search for in the knowledge base.
        max_results: The number of text chunks to return (default 5).

    Returns:
        A formatted string containing the internal document chunks that best match the query.
    """
    try:
        matches = knowledge_indexer.query_knowledge(query, n_results=max_results)
        
        if not matches:
            return "No matches found in the Knowledge Base. Are you sure the user uploaded relevant documents?"

        response = f"Found {len(matches)} matches in the Knowledge Base:\n\n"
        for i, match in enumerate(matches):
            response += f"--- Result {i+1} from Document: '{match['filename']}' ---\n"
            response += f"{match['content']}\n\n"
            
        return response

    except Exception as e:
        return f"Error querying Knowledge Base: {e}"
