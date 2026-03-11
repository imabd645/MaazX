from core.gmail_handler import gmail_handler
from core.tool_registry import register_tool

@register_tool
def gmail_search_emails(query: str, max_results: int = 5):
    """
    Search for emails in the user's Gmail account using a query.
    Example query: 'from:boss', 'subject:meeting', 'after:2024/01/01'.
    """
    return gmail_handler.search_messages(query, max_results)

@register_tool
def gmail_read_email(message_id: str):
    """
    Read the full content of a specific email by its ID.
    The ID can be obtained from gmail_search_emails.
    """
    return gmail_handler.read_message(message_id)

@register_tool
def gmail_send_email(recipient: str, subject: str, body: str):
    """
    Compose and send a new email via Gmail.
    """
    return gmail_handler.send_email(recipient, subject, body)
