"""Tool: run_command — executes a shell command and returns stdout/stderr.

Security hardening:
- We apply a very small deny‑list of obviously dangerous commands
  (e.g. full‑disk wipes, shutdown) to reduce accidental damage.
- For anything more advanced, prefer running commands manually in your own shell.
"""

import os
import subprocess
from core.tool_registry import register_tool


def _is_dangerous_command(command: str) -> bool:
    """Best‑effort guard against obviously destructive commands.

    This is intentionally conservative: it blocks only a few patterns that
    are almost never desired from an automated agent.
    """
    cmd = command.strip().lower()

    # Unix‑style catastrophic patterns
    dangerous_substrings = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        " :(){ :|:& };:",  # fork bomb
    ]

    # Windows‑style catastrophic patterns
    dangerous_substrings += [
        "format c:",
        "format d:",
        "shutdown /s",
        "shutdown /r",
        "del /s /q c:\\",
    ]

    return any(pattern in cmd for pattern in dangerous_substrings)


@register_tool
def run_command(command: str, working_directory: str = ".") -> str:
    """Runs a shell command and returns its output. Use for tasks like running tests,
    installing packages, git operations, or any CLI tool.

    Args:
        command: The shell command to execute (e.g. 'python -m pytest', 'git status').
        working_directory: The directory to run the command in (default is current directory).
    """
    try:
        if _is_dangerous_command(command):
            return (
                "Blocked: Command matches a deny‑listed pattern that could be destructive.\n"
                "Please run this manually in your own terminal if you really intend to execute it."
            )

        # Normalize working directory to an absolute path for clarity
        cwd = os.path.abspath(working_directory or ".")

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd,
            encoding='utf-8',
            errors='replace'
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
