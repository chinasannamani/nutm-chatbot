"""
Prints the Subresource Integrity (SRI) tag for widget.js.

Why: if the chat widget is loaded from a different website than the page that
uses it (for example from your hosting address into nutm.edu.ng), the browser
will refuse to run widget.js if even one character of it has been changed.

Run:   python make_sri.py https://nutm-chatbot.onrender.com/widget.js
Run it again whenever you change widget.js, and paste the new tag.
"""
import base64
import hashlib
import sys
from pathlib import Path

data = Path(__file__).with_name("widget.js").read_bytes()
digest = "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()
url = sys.argv[1] if len(sys.argv) > 1 else "https://nutm-chatbot.onrender.com/widget.js"
print("Paste this into the page, just before </body>:\n")
print(f'<script src="{url}"\n        integrity="{digest}"\n        crossorigin="anonymous"></script>')
