#!/usr/bin/env python3
"""Local preview with Cloudflare Pages-style clean URLs: /about serves about.html, /guides/ serves guides/index.html.

    python3 tools/serve.py [port]    # default $PORT or 4321
"""

import http.server
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class CleanURLHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path):
        local = Path(super().translate_path(path))
        if not local.exists() and local.with_suffix(".html").exists():
            return str(local.with_suffix(".html"))
        return str(local)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class DualStackServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 4321))
    DualStackServer(("::", port), CleanURLHandler).serve_forever()
