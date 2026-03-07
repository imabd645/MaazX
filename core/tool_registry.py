"""
Tool Registry — collects every tool function so the agent can discover them.

To add a new tool:
  1. Create a new file in  tools/  (e.g. tools/my_tool.py)
  2. Define a plain function with a clear docstring + type-hinted args.
  3. Decorate it with  @register_tool

The registry is a simple list; the agent passes it straight to Gemini.
"""

_registry: list = []


def register_tool(func):
    """Decorator that adds a function to the global tool list."""
    _registry.append(func)
    return func


def get_all_tools() -> list:
    """Return every registered tool function."""
    return list(_registry)
