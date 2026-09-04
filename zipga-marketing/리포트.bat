@echo off
chcp 65001 >nul
cd /d "%~dp0reports"
echo 마케팅 리포트를 만듭니다...
echo.
python report.py
echo.
pause
