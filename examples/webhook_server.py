"""Receive and verify SonoVault webhook deliveries.

1. Register the endpoint: sv.webhooks.create(url="https://your.host/webhooks/sonovault")
2. Store the returned secret (shown only once) in SONOVAULT_WEBHOOK_SECRET.
Run: SONOVAULT_WEBHOOK_SECRET=whsec_... python examples/webhook_server.py

Uses only the standard library. In a real app, use your web framework's
raw-body access and call verify_webhook_signature the same way.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from sonovault import verify_webhook_signature

SECRET = os.environ["SONOVAULT_WEBHOOK_SECRET"]


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhooks/sonovault":
            self.send_response(404)
            self.end_headers()
            return

        # Read the RAW body. Verify before parsing JSON.
        payload = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        ok = verify_webhook_signature(
            secret=SECRET,
            header=self.headers.get("SonoVault-Signature", ""),
            payload=payload,
        )
        if not ok:
            self.send_response(400)
            self.end_headers()
            return

        event = json.loads(payload)
        # Dedupe on the stable event id: deliveries are retried on failure.
        track = event["data"].get("track") or {}
        print(event["id"], event["type"], event["data"]["stream_id"], track.get("title", ""))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass  # keep stdout for events


if __name__ == "__main__":
    print("Listening on :8787")
    HTTPServer(("", 8787), WebhookHandler).serve_forever()
