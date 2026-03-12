' Invisible Launcher for Gemini AI Agent
' This script runs the Python web_app.py without showing a console window.

Set WshShell = CreateObject("WScript.Shell")

' Get the directory of the current script
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Command to run: python web_app.py
' The "0" at the end means "Hidden Window"
' The "False" at the end means "Don't wait for completion"

' Show a temporary popup for feedback (disappears after 2 seconds)
WshShell.Popup "Starting Gemini AI Agent in background...", 2, "Agent Launcher", 64

WshShell.Run "python """ & strPath & "\web_app.py""", 0, False
