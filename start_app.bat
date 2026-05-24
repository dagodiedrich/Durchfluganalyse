@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv
)

call ".venv\Scripts\activate.bat"
pip install -r requirements.txt >nul
python launcher.py
