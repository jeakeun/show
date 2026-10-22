@echo off
rem Agent Factory launcher. ASCII only (CP949 safe).
rem Double-click: menu. Or: start.bat design "situation" / start.bat run report-trend
setlocal
cd /d "%~dp0"
rem venv lives outside OneDrive (OneDrive made files cloud-only before, 2026-08-07)
set "VENV=%LOCALAPPDATA%\agent-factory-venv"
if not exist "%VENV%\Scripts\python.exe" (
  echo [setup] creating python env at %VENV% ...
  py -3.12 -m venv "%VENV%" || py -3 -m venv "%VENV%"
)
"%VENV%\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo [error] package install failed. Check internet and try again.
  pause
  exit /b 1
)
set PYTHONUTF8=1
chcp 65001 >nul
"%VENV%\Scripts\python.exe" -m agent_factory %*
pause
