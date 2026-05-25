#!/usr/bin/env python3
"""Prueft, ob alle Dateien fuer den Start vorhanden sind."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED_DIRS = ("templates", "static", "upload", "output")
REQUIRED_FILES = (
    "app.py",
    "launcher.py",
    "detector.py",
    "report_pdf.py",
    "requirements.txt",
    "templates/index.html",
    "static/app.js",
    "static/styles.css",
)


def main() -> int:
    print(f"Projektordner: {ROOT}")
    ok = True
    for name in REQUIRED_DIRS:
        path = ROOT / name
        if path.is_dir():
            print(f"  OK  {name}/")
        else:
            print(f"  FEHLT  {name}/")
            ok = False
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if path.is_file():
            print(f"  OK  {rel}")
        else:
            print(f"  FEHLT  {rel}")
            ok = False
    if ok:
        print("\nSetup ist vollstaendig. Start mit: python launcher.py")
        return 0
    print("\nSetup unvollstaendig. Bitte komplettes Repository klonen/entpacken.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
