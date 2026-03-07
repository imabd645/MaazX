"""Tool: run_command — executes a shell command and returns stdout/stderr."""

import subprocess
from core.tool_registry import register_tool


@register_tool
def run_command(command: str, working_directory: str = ".") -> str:
    """Runs a shell command and returns its output. Use for tasks like running tests,
    installing packages, git operations, or any CLI tool.

    Args:
        command: The shell command to execute (e.g. 'python -m pytest', 'git status').
        working_directory: The directory to run the command in (default is current directory).
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=working_directory,
        )

        output_parts = []
        if result.stdout.strip():
            output_parts.append(f"STDOUT:\n{result.stdout.strip()}")
        if result.stderr.strip():
            output_parts.append(f"STDERR:\n{result.stderr.strip()}")

        status = f"Exit code: {result.returncode}"
        output = "\n\n".join(output_parts) if output_parts else "(no output)"

        return f"{status}\n{output}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"Error running command: {e}"
