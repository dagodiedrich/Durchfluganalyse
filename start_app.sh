#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[FEHLER] python3 nicht gefunden. Bitte Python 3.10+ installieren (https://www.python.org/downloads/)."
  exit 1
fi

if [ ! -d "templates" ] || [ ! -d "static" ]; then
  echo "[FEHLER] Ordner templates/ und static/ fehlen in diesem Verzeichnis:"
  echo "  $(pwd)"
  echo "Bitte das komplette Projekt herunterladen (git clone oder ZIP), nicht nur einzelne Dateien."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
python launcher.py
