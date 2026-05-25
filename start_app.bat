@echo off
setlocal
cd /d "%~dp0"

if not exist "templates\" (
  echo [FEHLER] Ordner templates\ fehlt. Bitte das komplette Projekt entpacken, nicht nur einzelne Dateien.
  pause
  exit /b 1
)
if not exist "static\" (
  echo [FEHLER] Ordner static\ fehlt. Bitte das komplette Projekt entpacken, nicht nur einzelne Dateien.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv
)

call ".venv\Scripts\activate.bat"
pip install -r requirements.txt >nul
python launcher.py
