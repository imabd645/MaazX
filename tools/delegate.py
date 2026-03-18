"""
delegate_task — Allows the main MaazX agent to spawn specialized sub-agents
for focused tasks like research, coding, or data analysis.
"""

from core.tool_registry import register_tool


@register_tool
def delegate_task(task: str, role: str = "researcher", context: str = "") -> str:
    """
    Delegate a focused task to a specialized sub-agent.

    Available roles:
      - 'researcher': Web search and knowledge base queries. Best for gathering information.
      - 'coder': File operations and shell commands. Best for writing/editing code and running tests.
      - 'analyst': Database queries and Python scripting. Best for data analysis and insights.

    Args:
        task: Clear, self-contained description of what the sub-agent should accomplish.
        role: The specialist role to assign (researcher, coder, analyst).
        context: Optional extra context or constraints for the sub-agent.

    Returns:
        The sub-agent's complete response with findings or results.
    """
    from core.sub_agents import run_sub_agent
    
    if not task.strip():
        return "Error: Task description cannot be empty."
    
    valid_roles = ["researcher", "coder", "analyst"]
    if role not in valid_roles:
        return f"Error: Invalid role '{role}'. Choose from: {', '.join(valid_roles)}"
    
    print(f"\n[Delegate] Main agent delegating to '{role}': {task[:100]}...")
    
    result = run_sub_agent(task=task, role=role, context=context)
    
    # Format the response so the orchestrator can present it cleanly
    header = f"[{role.upper()} AGENT REPORT]"
    return f"{header}\n{result}"
