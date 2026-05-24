from __future__ import annotations

import threading
import time
import webbrowser

from app import app


HOST = "127.0.0.1"
PORT = 5050
URL = f"http://{HOST}:{PORT}"


def _open_browser_when_ready() -> None:
    # Give Flask a short head start, then open UI.
    time.sleep(1.2)
    webbrowser.open_new(URL)


if __name__ == "__main__":
    opener = threading.Thread(target=_open_browser_when_ready, daemon=True)
    opener.start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
