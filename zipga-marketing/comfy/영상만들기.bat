@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo scenes.txt 의 장면들로 영상을 만듭니다.
echo (장면 수정은 scenes.txt 를 메모장으로 열어서 하세요)
echo.
python comfy.py --scenes scenes.txt --out 새영상.mp4 --mp 1.0
echo.
pause
