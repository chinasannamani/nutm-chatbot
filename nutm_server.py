"""
NUTM chatbot - web server (standard library only, no pip install needed).

Run:   python nutm_server.py            (on your computer)
       python nutm_server.py --lan      (also reachable from phones on your Wi-Fi)
       python nutm_server.py --port 8080 --no-browser
On Render the start command is simply:  python nutm_server.py
Then open:
    http://localhost:8000/        -> full-page chatbot
    http://localhost:8000/demo    -> mock NUTM website with the chat widget embedded

Keep these files in the same folder:
    nutm_chatbot.py, nutm_knowledge_base.txt, nutm_server.py,
    chat.html, demo_site.html, widget.js, nutm_logo.png, nutm_icon.png

Optional settings (environment variables, useful when hosted):
    PORT                port to listen on (set automatically by Render and other hosts; default 8000)
    HOST                address to listen on (default 127.0.0.1 on your computer, 0.0.0.0 when hosted)
    ALLOWED_ORIGINS     comma-separated websites allowed to use/embed the chatbot,
                        e.g. https://nutm-chatbot.onrender.com,https://www.nutm.edu.ng
                        (default: any website - fine for a demo, set it for real use)
    RATE_LIMIT          questions allowed per visitor per minute (default 120)
    GLOBAL_RATE_LIMIT   questions allowed from everyone together per minute (default 600)
    TRUSTED_PROXY_HOPS  how many proxies sit in front of the server (default 1)
    MAX_CONNECTIONS     simultaneous requests handled (default 50)
"""

import argparse
import errno
import json
import os
import socket
import sys
import threading
import time
import webbrowser
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import nutm_chatbot as bot

HERE = Path(__file__).parent

# Where is the server running?
#  * On Render (or any host that sets PORT / RENDER): listen on all network interfaces, on the port
#    the platform gives us.
#  * On your own computer: listen only on this computer (127.0.0.1), on port 8000.
# Either can be changed with the HOST / PORT variables or with --host / --port / --lan (see main()).
DEPLOYED = any(k in os.environ for k in ("PORT", "RENDER", "DEPLOYED"))
HOST = os.environ.get("HOST") or ("0.0.0.0" if DEPLOYED else "127.0.0.1")
try:
    PORT = int(os.environ.get("PORT", "8000"))
except ValueError:
    PORT = 8000

MAX_BODY = 4096          # bytes accepted in one request
MAX_MESSAGE = 200        # characters of a question that are used
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "120"))
GLOBAL_LIMIT = int(os.environ.get("GLOBAL_RATE_LIMIT", "600"))
RATE_WINDOW = 60         # seconds
PROXY_HOPS = max(1, int(os.environ.get("TRUSTED_PROXY_HOPS", "1")))
MAX_CONNECTIONS = int(os.environ.get("MAX_CONNECTIONS", "50"))
ALLOWED = [o.strip().rstrip("/") for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
EXTRA_ORIGINS = [o for o in ALLOWED if o != "*"]

PAGES = {
    "/": ("chat.html", "text/html; charset=utf-8"),
    "/demo": ("demo_site.html", "text/html; charset=utf-8"),
    "/widget.js": ("widget.js", "application/javascript; charset=utf-8"),
    "/nutm_logo.png": ("nutm_logo.png", "image/png"),
    "/nutm_icon.png": ("nutm_icon.png", "image/png"),
}

retriever = bot.Retriever(bot.load_entries(bot.KB_FILE))

_hits = defaultdict(deque)
_global_hits = deque()
_lock = threading.Lock()


def rate_limited(ip):
    """True if this visitor (or everyone together) has asked too many questions lately."""
    now = time.time()
    with _lock:
        while _global_hits and now - _global_hits[0] > RATE_WINDOW:
            _global_hits.popleft()
        q = _hits[ip]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT or len(_global_hits) >= GLOBAL_LIMIT:
            return True
        q.append(now)
        _global_hits.append(now)
        if len(_hits) > 5000:  # keep memory small even if many addresses appear
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > RATE_WINDOW]:
                _hits.pop(k, None)
        return False


class Handler(BaseHTTPRequestHandler):
    timeout = 10                      # drop connections that stall
    server_version = "NUTM-Chatbot"   # do not reveal Python/server versions
    sys_version = ""

    def _send(self, status, body, content_type, head=False, page=False, cache="no-store"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if page:  # HTML pages only
            ancestors = " ".join(["'self'"] + EXTRA_ORIGINS)
            self.send_header("Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
                f"form-action 'none'; frame-ancestors {ancestors}")
            if not EXTRA_ORIGINS:
                self.send_header("X-Frame-Options", "SAMEORIGIN")
        if DEPLOYED and self.headers.get("X-Forwarded-Proto", "") == "https":
            self.send_header("Strict-Transport-Security", "max-age=31536000")
        origin = self.headers.get("Origin", "").rstrip("/")
        if "*" in ALLOWED:
            self.send_header("Access-Control-Allow-Origin", "*")
        elif origin in ALLOWED:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _reply(self, status, text, context=None):
        payload = {"reply": text}
        if context is not None:
            payload["context"] = context  # lets the browser continue the same conversation
        body = json.dumps(payload).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _client_ip(self):
        """Visitor address. Behind a proxy, take the entry the trusted proxy added
        (counting from the right), because the left side can be faked by the visitor."""
        xff = self.headers.get("X-Forwarded-For", "")
        if DEPLOYED and xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                return parts[-min(PROXY_HOPS, len(parts))]
        return self.client_address[0]

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain")

    def _serve_get(self, head):
        try:
            path = self.path.split("?")[0]
            if path == "/health":
                self._send(200, b"ok", "text/plain", head)
            elif path in PAGES:
                filename, ctype = PAGES[path]
                is_page = ctype.startswith("text/html")
                cache = "public, max-age=3600" if ctype == "image/png" else "no-cache"
                self._send(200, (HERE / filename).read_bytes(), ctype, head, page=is_page, cache=cache)
            else:
                self._send(404, b"Not found", "text/plain", head)
        except Exception as exc:  # e.g. a missing file: answer instead of dropping the connection
            print("[server] error:", type(exc).__name__)
            try:
                self._send(500, b"Server error", "text/plain", head)
            except Exception:
                pass

    def do_GET(self):
        self._serve_get(head=False)

    def do_HEAD(self):
        self._serve_get(head=True)

    def do_POST(self):
        try:
            if self.path.split("?")[0] != "/chat":
                self._send(404, b"Not found", "text/plain")
                return
            if rate_limited(self._client_ip()):
                self._reply(429, "You are sending questions too quickly. Please wait a minute and try again.")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0:
                self._reply(400, "Sorry, I could not read that request.")
                return
            if length > MAX_BODY:
                self._reply(413, "Your message is too long. Please ask a shorter question.")
                return
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, RecursionError):
                data = None
            if not isinstance(data, dict):
                self._reply(400, "Sorry, I could not read that request.")
                return
            message = str(data.get("message") or "").strip()[:MAX_MESSAGE]
            ctx = bot.sanitize_context(retriever, data.get("context"))
            reply = bot.answer(retriever, message, ctx) if message else "Please type a question."
            self._reply(200, reply, ctx)
        except Exception as exc:  # never leave the visitor without a response
            print("[server] error:", type(exc).__name__)
            try:
                self._reply(500, "Sorry, something went wrong. Please try again.")
            except Exception:
                pass

    def log_message(self, fmt, *args):
        """Log request lines only (questions are never logged), stripping control characters."""
        line = fmt % args
        print("[server]", "".join(ch if ch.isprintable() else "?" for ch in line)[:200])


class LimitedServer(ThreadingHTTPServer):
    """Threaded server that refuses new connections when too many are already being handled."""
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._slots = threading.BoundedSemaphore(MAX_CONNECTIONS)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
            self.shutdown_request(request)
            return
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def lan_address():
    """This computer's address on the local network (so phones on the same Wi-Fi can connect)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("10.255.255.255", 1))  # no data is sent
            return sock.getsockname()[0]
    except OSError:
        return None


def main():
    global HOST, PORT
    ap = argparse.ArgumentParser(description="NUTM chatbot web server")
    ap.add_argument("--host", help="address to listen on (default: 127.0.0.1 on your computer, 0.0.0.0 when hosted)")
    ap.add_argument("--port", type=int, help="port to listen on (default: 8000, or the PORT variable when hosted)")
    ap.add_argument("--lan", action="store_true", help="also let phones/computers on your Wi-Fi use the chatbot")
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser tab automatically")
    args = ap.parse_args()
    if args.lan:
        HOST = "0.0.0.0"
    if args.host:
        HOST = args.host
    if args.port:
        PORT = args.port

    server = None
    # on your computer, move to the next port if 8000 is already in use; when hosted, never change it
    ports = [PORT] if (DEPLOYED or args.port) else range(PORT, PORT + 10)
    for port in ports:
        try:
            server = LimitedServer((HOST, port), Handler)
            PORT = port
            break
        except OSError as exc:
            if exc.errno not in (errno.EADDRINUSE, 10048) or DEPLOYED or args.port:
                raise
            print(f"Port {port} is busy, trying {port + 1} ...")
    if server is None:
        sys.exit("No free port found. Close other programs or choose one with --port.")

    local_url = f"http://localhost:{PORT}/"
    print(f"NUTM chatbot running on port {PORT}")
    if DEPLOYED:
        print("Public address:", os.environ.get("RENDER_EXTERNAL_URL", "see your hosting dashboard"))
    else:
        print("On this computer :", local_url, "  (demo page:", local_url + "demo)")
        if HOST == "0.0.0.0":
            lan = lan_address()
            if lan:
                print("On your Wi-Fi    :", f"http://{lan}:{PORT}/")
    if DEPLOYED and "*" in ALLOWED:
        print("WARNING: ALLOWED_ORIGINS is not set, so any website can use this chatbot. "
              "Set it to your own site(s) for real use.")
    print("Press Ctrl+C to stop.")
    if not DEPLOYED and not args.no_browser:  # only open a browser tab on your own computer
        threading.Timer(1.0, lambda: webbrowser.open(local_url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()
