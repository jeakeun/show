@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 배경음악을 만듭니다 (약 3~5분)
echo.
python make_music.py
echo.
pause
