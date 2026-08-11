"""Entry point for the bundled desktop app (see `scripts/build_desktop.py`).

Not used in normal development — `uv run uvicorn app.main:app --reload` still
covers that, same as always. This is specifically what PyInstaller points at
to produce a double-click host launcher: start the server, open the host's
browser to it, and print the LAN URL other players' phones need — since a
`--windowed` build has no console for them to read that from otherwise, it
also gets written to a log file next to the app's data directory.
"""

import logging
import socket
import threading
import time
import webbrowser

import uvicorn

PORT = 8000


def _lan_ip() -> str:
    """Best-effort LAN IP so the URL we print is one other players' phones
    on the same WiFi can actually reach — not just localhost."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _setup_logging() -> logging.Logger:
    from app.db import DATA_DIR  # imported here so DATA_DIR's frozen-aware logic already ran

    log_path = DATA_DIR / "launcher.log"
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger = logging.getLogger("monopoly_os.launcher")
    logger.info("monopoly_OS launcher starting (log file: %s)", log_path)
    return logger


def _open_browser_when_ready(logger: logging.Logger) -> None:
    for _ in range(50):  # ~10s of polling before giving up
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.2):
                break
        except OSError:
            time.sleep(0.2)
    webbrowser.open(f"http://localhost:{PORT}")
    logger.info("Opened browser to http://localhost:%s", PORT)


def main() -> None:
    logger = _setup_logging()
    host_ip = _lan_ip()
    logger.info("Host device:  http://localhost:%s", PORT)
    logger.info("Other phones (same WiFi): http://%s:%s", host_ip, PORT)

    threading.Thread(target=_open_browser_when_ready, args=(logger,), daemon=True).start()

    from app.main import app  # deferred so logging is configured first

    try:
        uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
    except Exception:
        logger.exception("Server crashed")
        raise


if __name__ == "__main__":
    main()
