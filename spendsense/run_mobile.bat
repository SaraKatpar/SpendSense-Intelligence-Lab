@echo off
cd /d "%~dp0"
set "MOBILE_PYTHON=python"
if exist "..\.venv\Scripts\python.exe" set "MOBILE_PYTHON=..\.venv\Scripts\python.exe"
echo SpendSense Mobile: http://127.0.0.1:8765
echo Keep this window open while using the app.
"%MOBILE_PYTHON%" -m uvicorn mobile.api:app --host 127.0.0.1 --port 8765 --no-access-log
pause
