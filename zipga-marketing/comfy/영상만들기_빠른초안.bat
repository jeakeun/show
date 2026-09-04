@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 빠른 초안 화질로 만듭니다 (느낌만 확인할 때)
echo.
python comfy.py --scenes scenes.txt --out 초안영상.mp4 --draft
echo.
pause
