@echo off
setlocal

cd /d %~dp0

if not exist .venv (
  echo [SIGNAL.AI] Creating virtual environment...
  py -3 -m venv .venv
)

call .venv\Scripts\activate.bat

echo [SIGNAL.AI] Upgrading pip...
python -m pip install --upgrade pip

echo [SIGNAL.AI] Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [SIGNAL.AI] Dependency installation failed.
  pause
  exit /b 1
)

echo [SIGNAL.AI] Starting local web app at http://127.0.0.1:8000
python run_local.py

endlocal
