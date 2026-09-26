"""REST API for MoMo SMS transactions, built on Python's http.server (no
external framework).

Endpoints (all require Basic Auth - see api/auth.py):
    GET    /transactions       list all transactions
    GET    /transactions/{id}  view one transaction
    POST   /transactions       add a new transaction
    PUT    /transactions/{id}  update an existing transaction
    DELETE /transactions/{id}  delete a transaction

Run: python -m api.app  (serves on API_HOST:API_PORT, see .env.example)
"""

from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from api.auth import check_basic_auth
from dsa.storage import TransactionStore, load_store

TRANSACTION_ITEM_RE = re.compile(r"^/transactions/(\d+)/?$")
STORE: TransactionStore = load_store()


class TransactionRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _authorized(self) -> bool:
        """Returns True if the request is authorized; otherwise sends the
        401/501 response itself and returns False (caller should stop)."""
        try:
            ok = check_basic_auth(self.headers.get("Authorization"))
        except NotImplementedError:
            self._send_json(501, {"error": "Auth not implemented yet - see api/auth.py TODO"})
            return False
        if not ok:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="transactions"')
            self.send_header("Content-Type", "application/json")
            body = json.dumps({"error": "Unauthorized"}).encode("utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return False
        return True

    def do_GET(self) -> None:
        if not self._authorized():
            return
        if self.path.rstrip("/") == "/transactions":
            self._send_json(200, STORE.list())
            return
        match = TRANSACTION_ITEM_RE.match(self.path)
        if match:
            record = STORE.get(int(match.group(1)))
            if record is None:
                self._send_json(404, {"error": "Transaction not found"})
            else:
                self._send_json(200, record)
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if not self._authorized():
            return
        if self.path.rstrip("/") != "/transactions":
            self._send_json(404, {"error": "Not found"})
            return
        body = self._read_json_body()
        if body is None:
            self._send_json(400, {"error": "Request body must be valid JSON"})
            return
        # TODO: validate required fields before creating the record.
        record = STORE.create(body)
        self._send_json(201, record)

    def do_PUT(self) -> None:
        if not self._authorized():
            return
        match = TRANSACTION_ITEM_RE.match(self.path)
        if not match:
            self._send_json(404, {"error": "Not found"})
            return
        body = self._read_json_body()
        if body is None:
            self._send_json(400, {"error": "Request body must be valid JSON"})
            return
        record = STORE.update(int(match.group(1)), body)
        if record is None:
            self._send_json(404, {"error": "Transaction not found"})
        else:
            self._send_json(200, record)

    def do_DELETE(self) -> None:
        if not self._authorized():
            return
        match = TRANSACTION_ITEM_RE.match(self.path)
        if not match:
            self._send_json(404, {"error": "Not found"})
            return
        deleted = STORE.delete(int(match.group(1)))
        if deleted:
            self.send_response(204)
            self.end_headers()
        else:
            self._send_json(404, {"error": "Transaction not found"})

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


def run(host: str | None = None, port: int | None = None) -> None:
    host = host or os.environ.get("API_HOST", "0.0.0.0")
    port = port or int(os.environ.get("API_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), TransactionRequestHandler)
    print(f"Serving {len(STORE.list())} transactions on http://{host}:{port} (Basic Auth required)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    run()
