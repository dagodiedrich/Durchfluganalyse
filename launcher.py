from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app  # noqa: E402


HOST = "127.0.0.1"
PORT = 5050
URL = f"http://{HOST}:{PORT}"


def _open_browser_when_ready() -> None:
    time.sleep(1.2)
    webbrowser.open_new(URL)


if __name__ == "__main__":
    opener = threading.Thread(target=_open_browser_when_ready, daemon=True)
    opener.start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
