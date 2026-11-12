@echo off
if defined ORBIT_AGENT_KEY goto launch
if defined ORBIT_AGENT_KEY_FILE goto launch
echo Sign in to Orbit and open MCP ^& Skills to copy your account-specific Claude Code setup.
start "" "http://127.0.0.1:47831/#agents"
pause
exit /b
:launch
call claude.cmd --plugin-dir "%~dp0agent-connections\claude-code"
if errorlevel 1 pause
