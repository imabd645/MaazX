@echo off
:: Setup Startup for Gemini AI Agent
:: This script creates a shortcut in the Windows Startup folder

set SCRIPT_PATH=%~dp0InvisibleLauncher.vbs
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_NAME=GeminiAgentLauncher.lnk

echo [System] Creating startup shortcut...
echo [System] Launcher path: %SCRIPT_PATH%

powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut('%STARTUP_FOLDER%\%SHORTCUT_NAME%');$s.TargetPath='%SCRIPT_PATH%';$s.WorkingDirectory='%~dp0';$s.Save()"

echo.
echo [DONE] Agent is now set to start automatically on login!
echo [DONE] You can find the shortcut in: %STARTUP_FOLDER%
echo.
pause
