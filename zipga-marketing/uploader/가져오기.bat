@echo off
chcp 65001 >nul
cd /d "%~dp0"
python comfy_fetch.py
echo.
pause
