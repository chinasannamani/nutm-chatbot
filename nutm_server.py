"""
NUTM chatbot - local web server (standard library only, no pip install needed).

Run:   python nutm_server.py
Then open:
    http://localhost:8000/        -> full-page chatbot
    http://localhost:8000/demo    -> mock NUTM website with the chat widget embedded

Keep these files in the same folder:
    nutm_chatbot.py, nutm_knowledge_base.txt, nutm_server.py,
    chat.html, demo_site.html, widget.js, nutm_logo.png, nutm_icon.png
"""

import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import nutm_chatbot as bot

HERE = Path(__file__).parent
HOST, PORT = "127.0.0.1", 8000

PAGES = {
    "/": ("chat.html", "text/html; charset=utf-8"),
    "/demo": ("demo_site.html", "text/html; charset=utf-8"),
    "/widget.js": ("widget.js", "application/javascript; charset=utf-8"),
    "/nutm_logo.png": ("nutm_logo.png", "image/png"),
    "/nutm_icon.png": ("nutm_icon.png", "image/png"),
}

retriever = bot.Retriever(bot.load_entries(bot.KB_FILE))


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # CORS: lets the widget work when embedded on a different website
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in PAGES:
            filename, ctype = PAGES[path]
            self._send(200, (HERE / filename).read_bytes(), ctype)
        else:
            self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        if self.path != "/chat":
            self._send(404, b"Not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            message = str(data.get("message", "")).strip()[:500]
        except (ValueError, json.JSONDecodeError):
            self._send(400, b'{"error": "bad request"}', "application/json")
            return
        reply = bot.answer(retriever, message) if message else "Please type a question."
        body = json.dumps({"reply": reply}).encode("utf-8")
        self._send(200, body, "application/json; charset=utf-8")

    def log_message(self, fmt, *args):  # quieter console
        print("[server]", fmt % args)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print(f"NUTM chatbot running at {url}  (demo page: {url}demo)")
    print("Press Ctrl+C to stop.")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()
