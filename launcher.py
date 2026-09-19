"""Double-click launcher for the self-contained Windows portfolio demo."""

import os
import socket
import threading
import webbrowser

from app import create_app


def find_available_port(preferred=5000):
    for port in (preferred, 5050, 8000, 8080):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No free local port was found.")


def main():
    os.environ.setdefault("DEMO_MODE", "true")
    os.environ.setdefault("DATABASE_URL", "sqlite:///instance/executable-demo.db")
    port = find_available_port()
    url = f"http://127.0.0.1:{port}"
    print("=" * 62)
    print(" SYSTEMATIC REVIEW TOOL - PORTFOLIO DEMO")
    print("=" * 62)
    print(f"The application will open automatically at {url}")
    print("Keep this window open while using the demo.")
    print("Close this window or press Ctrl+C to stop the application.")
    print("=" * 62)
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    create_app().run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

