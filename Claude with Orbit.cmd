@echo off
call claude.cmd --plugin-dir "%~dp0agent-connections\claude-code"
if errorlevel 1 pause
