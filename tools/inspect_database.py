"""Tool: inspect_database — allows the AI to securely run SELECT queries on local SQLite databases."""

import sqlite3
import os
import re
from core.tool_registry import register_tool

def _resolve_db_path(db_name: str) -> str:
    """Resolves the given database name to an absolute path.
    If it's just a filename like 'agent_data.db', it looks in the project root.
    """
    if os.path.isabs(db_name):
        return db_name
    
    # Assume it's in the project root relative to this current file
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(root_dir, db_name)

@register_tool
def get_database_schema(db_path: str = "agent_data.db") -> str:
    """
    Fetches the complete schema (tables and columns) of a local SQLite database.
    Use this BEFORE writing SQL queries so you know what tables and columns exist!
    
    Args:
        db_path: The name or path of the SQLite database (default is 'agent_data.db').
        
    Returns:
        A formatted string describing all tables and their SQL creation statements.
    """
    full_path = _resolve_db_path(db_path)
    if not os.path.exists(full_path):
        return f"Error: Database file not found at {full_path}"
        
    try:
        conn = sqlite3.connect(full_path)
        cursor = conn.cursor()
        
        # Query sqlite_master to get all table schemas
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        
        if not tables:
            return f"Database {db_path} is empty or has no tables."
            
        schema_output = f"Schema for {db_path}:\n" + "="*40 + "\n"
        for table_name, sql in tables:
            schema_output += f"Table: {table_name}\n"
            schema_output += f"{sql}\n"
            schema_output += "-"*20 + "\n"
            
        conn.close()
        return schema_output
    except Exception as e:
        return f"Error reading schema: {str(e)}"

@register_tool
def run_sql_query(query: str, db_path: str = "agent_data.db") -> str:
    """
    Executes a raw SQL query against a local SQLite database and returns the results.
    SECURITY LOCK: This tool ONLY permits read-only SELECT or PRAGMA queries.
    
    Args:
        query: The exact SQL string to execute (e.g. "SELECT count(*) FROM whatsapp_contacts").
        db_path: The name or path of the SQLite database (default is 'agent_data.db').
        
    Returns:
        A formatted string containing the rows returned by the query, or an error message.
    """
    # 1. Enforce strict read-only safety check
    # Check for dangerous keywords anywhere in the query (case insensitive)
    dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'REPLACE', 'TRUNCATE']
    upper_query = query.upper()
    for keyword in dangerous_keywords:
        # Regex to prevent false positives like 'SELECT update_time FROM...'
        if re.search(r'\b' + keyword + r'\b', upper_query):
            return f"SECURITY ERROR: The '{keyword}' command is strictly blocked. You are only allowed to run SELECT or PRAGMA queries."
            
    # 2. Execute Query
    full_path = _resolve_db_path(db_path)
    if not os.path.exists(full_path):
        return f"Error: Database file not found at {full_path}"
        
    try:
        conn = sqlite3.connect(full_path)
        # Configure row factory to return dict-like objects for easily readable output
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            return "Query executed successfully, but returned 0 rows."
            
        # Format the output beautifully for the AI
        results = [dict(row) for row in rows]
        
        # Convert list of dicts to a readable string format
        output = f"Results ({len(rows)} rows):\n"
        for r in results:
            output += str(r) + "\n"
            
        conn.close()
        return output
    except Exception as e:
        return f"Database Query Error: {str(e)}"
