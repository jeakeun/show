@echo off
rem Read-only drive scan. Writes a report to the desktop. Deletes nothing.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 disk_scan.py %*
) else (
  python disk_scan.py %*
)
pause
