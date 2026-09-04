@echo off
chcp 65001 >nul
title 몽글이 버추얼 스트리머
cd /d "%~dp0"
echo.
echo  ================================
echo   몽글이 버추얼 스트리머 시작!
echo   이 검은 창은 끄지 말고 두세요
echo  ================================
echo.
start "" "http://localhost:8977"
where node >nul 2>nul
if %errorlevel%==0 (
  node server.js
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0server.ps1"
)
pause
