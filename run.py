import threading
import time
import webbrowser

from app import create_app

HOST = "127.0.0.1"
PORT = 5000  # mismo puerto por defecto de Flask

def open_browser():
    time.sleep(1)
    webbrowser.open(f"http://{HOST}:{PORT}")

if __name__ == "__main__":
    app = create_app()
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False)
