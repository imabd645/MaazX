"""
Python REPL Scratchpad Tool for MaazX.
Allows for direct execution of Python code with persistent state across calls.
"""

import sys
import io
import traceback
from core.tool_registry import register_tool

# In-memory storage for REPL sessions
# Key: session_id, Value: dict of global variables
repl_sessions = {}

@register_tool
def run_python_code(code: str, session_id: str = "default"):
    """
    Executes Python code in a persistent REPL session and returns the output.
    
    Args:
        code (str): The Python code snippet to execute.
        session_id (str): ID for the session to maintain state (e.g. variables, imports). Defaults to "default".
        
    Returns:
        dict: A dictionary containing 'output' (stdout), 'error' (stderr/traceback), and 'result' (return value of last expression).
    """
    if session_id not in repl_sessions:
        repl_sessions[session_id] = {
            "__builtins__": __builtins__
        }
    
    globals_dict = repl_sessions[session_id]
    
    # Capture stdout and stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    sys.stdout = stdout_capture
    sys.stderr = stderr_capture
    
    result = None
    error = None
    
    import ast
    
    try:
        # Parse the code into an AST
        tree = ast.parse(code)
        
        if not tree.body:
            return {"output": "", "error": "", "result": None}
            
        # Separate the last expression from the rest
        last_node = tree.body[-1]
        
        # Execute all nodes except the last one
        if len(tree.body) > 1:
            exec_tree = ast.Module(body=tree.body[:-1], type_ignores=[])
            exec(compile(exec_tree, filename="<ast>", mode="exec"), globals_dict)
            
        # If the last node is an expression, evaluate it to get a result
        if isinstance(last_node, ast.Expr):
            eval_tree = ast.Expression(body=last_node.value)
            result = eval(compile(eval_tree, filename="<ast>", mode="eval"), globals_dict)
        else:
            # Otherwise just execute it
            exec_tree = ast.Module(body=[last_node], type_ignores=[])
            exec(compile(exec_tree, filename="<ast>", mode="exec"), globals_dict)
            result = None
            
    except Exception:
        error = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
    return {
        "output": stdout_capture.getvalue(),
        "error": error or stderr_capture.getvalue(),
        "result": repr(result) if result is not None else None
    }
