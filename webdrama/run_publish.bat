@echo off
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
if not exist logs mkdir logs
"..\.venv\Scripts\python.exe" drama.py publish >> logs\publish.log 2>&1