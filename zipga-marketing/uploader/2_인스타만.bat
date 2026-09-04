@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".deps_ok" (
    echo 처음 실행 - 필요한 라이브러리를 설치합니다. 잠시만 기다려주세요...
    python -m pip install -q -r requirements.txt && echo ok> .deps_ok
)

echo === 인스타그램 에만 올립니다 ===
echo.
python upload.py --only instagram
echo.
pause
