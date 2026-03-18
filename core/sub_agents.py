"""
Sub-Agent Engine — Spawns specialized AI agents with focused system prompts
and restricted tool access for multi-agent collaboration.

The main MaazX agent acts as an orchestrator, delegating tasks to sub-agents
via the `delegate_task` tool.
"""

import datetime
from core.deepseek_client import chat_completion_with_tools


# ── Predefined Agent Roles ─────────────────────────────────────────────────

AGENT_ROLES = {
    "researcher": {
        "description": "Web research specialist — gathers information from the internet and knowledge base.",
        "system_prompt": (
            "You are a Research Agent, a specialized sub-agent of MaazX. "
            "Your ONLY job is to research a specific topic using web search and knowledge base tools, "
            "then return a clear, structured summary of your findings.\n\n"
            "RULES:\n"
            "- Be thorough: search multiple angles, verify facts across sources.\n"
            "- Return ONLY the research findings — no pleasantries.\n"
            "- Format output as a concise report with sections and bullet points.\n"
            "- Include source URLs when available.\n"
            "- If you cannot find information, say so explicitly.\n"
        ),
        "permitted_tools": [
            "search_web", "read_webpage", "query_knowledge", "semantic_search"
        ],
    },
    "coder": {
        "description": "Code engineer — writes, edits, and tests code.",
        "system_prompt": (
            "You are a Coding Agent, a specialized sub-agent of MaazX. "
            "Your ONLY job is to implement code changes as precisely described in your task.\n\n"
            "RULES:\n"
            "- ALWAYS read files before editing them.\n"
            "- Use absolute paths for all file operations.\n"
            "- Run tests or verification commands after every change.\n"
            "- Return a brief completion report listing files changed and test results.\n"
            "- If you encounter an error, fix it (max 2 retries) then report.\n"
        ),
        "permitted_tools": [
            "read_file", "create_file", "edit_file", "patch_file",
            "run_command", "search_in_files", "list_directory",
            "search_files", "semantic_search"
        ],
    },
    "analyst": {
        "description": "Data analyst — queries databases, runs scripts, and analyzes data.",
        "system_prompt": (
            "You are an Analysis Agent, a specialized sub-agent of MaazX. "
            "Your ONLY job is to analyze data, query databases, and produce insights.\n\n"
            "RULES:\n"
            "- Always call get_database_schema before writing any SQL.\n"
            "- Only use SELECT queries — never modify data.\n"
            "- Use python_repl for calculations and data processing.\n"
            "- Return structured findings with numbers and clear conclusions.\n"
        ),
        "permitted_tools": [
            "read_file", "python_repl", "run_sql_query",
            "get_database_schema", "search_in_files", "list_directory"
        ],
    },
}


def run_sub_agent(task: str, role: str, context: str = "") -> str:
    """
    Spawn a specialized sub-agent to complete a focused task.
    
    Args:
        task:    The specific task description for the sub-agent.
        role:    One of the predefined roles (researcher, coder, analyst).
        context: Optional additional context from the orchestrator.
    
    Returns:
        The sub-agent's final text reply.
    """
    if role not in AGENT_ROLES:
        available = ", ".join(AGENT_ROLES.keys())
        return f"Error: Unknown role '{role}'. Available roles: {available}"

    role_config = AGENT_ROLES[role]
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Build the sub-agent's system prompt
    system_prompt = (
        f"{role_config['system_prompt']}\n"
        f"[SYSTEM CLOCK] Current date/time: {current_time}\n"
    )
    
    if context:
        system_prompt += f"\nADDITIONAL CONTEXT FROM ORCHESTRATOR:\n{context}\n"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    print(f"\n[SubAgent] Spawning '{role}' agent for task: {task[:80]}...")

    try:
        import database
        settings = database.load_settings()
        model_name = settings.get("model_name", "deepseek-chat")
        
        result = chat_completion_with_tools(
            messages=messages,
            model_name=model_name,
            allow_tools=True,
            permitted_tools=role_config["permitted_tools"],
        )
        
        reply = result.get("reply", "Sub-agent returned no response.")
        tools_used = result.get("executed_tools", [])
        
        print(f"[SubAgent] '{role}' completed. Tools used: {len(tools_used)}")
        return reply

    except Exception as e:
        error_msg = f"Sub-agent ({role}) failed: {str(e)}"
        print(f"[SubAgent] {error_msg}")
        return error_msg
