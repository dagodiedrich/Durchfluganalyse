#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d "templates" ] || [ ! -d "static" ]; then
  echo "[FEHLER] templates/ und static/ muessen im Projektordner liegen."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[FEHLER] python3 nicht gefunden."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip -q
pip install -r requirements.txt pyinstaller -q

echo "[INFO] Baue macOS-App ..."
pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name Durchfluganalyse \
  --add-data "templates:templates" \
  --add-data "static:static" \
  launcher.py

echo ""
echo "[OK] Fertig. App liegt unter:"
echo "  $(pwd)/dist/Durchfluganalyse.app"
echo ""
echo "Hinweis: upload/ und output/ werden neben der .app im dist-Ordner angelegt,"
echo "wenn die App von dort gestartet wird. Fuer den Quellcode-Start: ./start_app.sh"
