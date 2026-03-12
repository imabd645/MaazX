@echo off
:: Stop Script for Gemini AI Agent
:: This script terminates all Python and Node processes.

echo [System] Stopping all Gemini Agent components...

:: Kill all Node processes
taskkill /f /im node.exe >nul 2>&1
echo [System] Stopped WhatsApp Bridge (Node.js).

:: Kill all Python processes
taskkill /f /im python.exe >nul 2>&1
echo [System] Stopped Gemini AI Agent (Python).

echo.
echo [DONE] All agent processes have been terminated.
echo.
pause
