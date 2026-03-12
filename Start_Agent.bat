@echo off
:: Start Script for Gemini AI Agent
:: This script launches the agent directly via Python.

echo [System] Starting Gemini AI Agent...

:: Launching directly. 
:: We use 'start' so the batch script can exit while the agent keeps running.
start /b python web_app.py

echo.
echo [DONE] The agent is now starting.
echo [INFO] You can close this window.
echo.
timeout /t 3
exit
