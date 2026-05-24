@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Erstelle virtuelle Umgebung...
  py -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

echo [INFO] Baue EXE...
pyinstaller ^
  --noconfirm ^
  --clean ^
  --name VideoanalyseStarter ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  launcher.py

echo.
echo [OK] Fertig. EXE liegt unter:
echo %cd%\dist\VideoanalyseStarter\VideoanalyseStarter.exe
echo.
pause
