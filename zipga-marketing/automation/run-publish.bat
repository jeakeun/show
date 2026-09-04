@echo off
REM 화, 금 오후 6시 영상 배포
REM Windows 작업 스케줄러에 이 파일을 등록하세요. 자세한 건 automation\README.md 참조.

chcp 65001 > nul
cd /d "%~dp0.."

for /f "tokens=1-3 delims=-/ " %%a in ("%date%") do set TODAY=%%a%%b%%c

echo [%date% %time%] 영상 배포 시작 >> "automation\logs\publish.log"

type "automation\publish-video.md" | claude -p "위 지시를 그대로 수행한다." ^
  --permission-mode dontAsk ^
  --output-format text >> "automation\logs\publish-%TODAY%.log" 2>&1

if %errorlevel% neq 0 (
  echo [%date% %time%] 실패 - 종료코드 %errorlevel% >> "automation\logs\publish.log"
  exit /b %errorlevel%
)

echo [%date% %time%] 완료 >> "automation\logs\publish.log"
