@echo off
cd /d "%~dp0"
python -m venv .orbit-mcp
if errorlevel 1 goto failed
".orbit-mcp\Scripts\python.exe" -m pip install -r requirements-mcp.txt
if errorlevel 1 goto failed
if not exist orbit-auth.json copy orbit-auth.example.json orbit-auth.json >nul
python agent_connections.py
if errorlevel 1 goto failed
echo Setup complete. Set your Supabase URL and publishable key in orbit-auth.json, then open Orbit.
pause
exit /b 0
:failed
echo Setup could not finish. Review the message above, correct it, and run setup again.
pause
exit /b 1
