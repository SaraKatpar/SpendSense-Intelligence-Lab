@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto failed
if exist requirements.lock.txt (
  ".venv\Scripts\python.exe" -m pip install -r requirements.lock.txt
) else (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
if errorlevel 1 goto failed
echo Setup complete. Double-click run.bat to open SpendSense.
pause
exit /b 0
:failed
echo Setup could not complete. Check the message above and your internet connection.
pause
exit /b 1
