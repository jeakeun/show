@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 콤피 서버 상태를 확인합니다...
python comfy.py --check
echo.
pause
