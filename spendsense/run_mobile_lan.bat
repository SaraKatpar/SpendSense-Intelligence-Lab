@echo off
cd /d "%~dp0"
set "MOBILE_PYTHON=python"
if exist "..\.venv\Scripts\python.exe" set "MOBILE_PYTHON=..\.venv\Scripts\python.exe"
echo SpendSense Mobile: http://127.0.0.1:8765
echo On your phone, use http://YOUR-LAPTOP-WIFI-IP:8765 on the same trusted Wi-Fi.
echo This preview uses HTTP. Use trusted HTTPS before entering real data over a network.
echo Keep this window open while using the app. Press Ctrl+C to stop.
"%MOBILE_PYTHON%" -m uvicorn mobile.api:app --host 0.0.0.0 --port 8765 --no-access-log
pause
