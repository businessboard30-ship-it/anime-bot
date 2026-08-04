"""
OPTIONAL cron-triggered endpoint for broadcasts queued by /broadcast.

Broadcasts are driven manually by default now -- the admin taps "Send Next
Batch" in Telegram (see handlers/broadcast_handler.py), no scheduler needed.
This endpoint is kept around only in case you later want to wire up an
external scheduler (e.g. cron-job.org) or Vercel Pro's per-minute cron
instead of tapping the button yourself. It is not required for broadcasts to
work and nothing calls it unless you set that up.

Auth: header "Authorization: Bearer <CRON_SECRET>" or query param ?secret=.
"""
import json
import asyncio
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from telegram import Bot

from config import BOT_TOKEN, CRON_SECRET
from modules.broadcast_runner import run_broadcast_batch

logger = logging.getLogger(__name__)


class handler(BaseHTTPRequestHandler):

    def _authorized(self) -> bool:
        if not CRON_SECRET:
            return False
        auth_header = self.headers.get("Authorization", "")
        if auth_header == f"Bearer {CRON_SECRET}":
            return True
        query = parse_qs(urlparse(self.path).query)
        return query.get("secret", [""])[0] == CRON_SECRET

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def _handle(self):
        if not self._authorized():
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Unauthorized"}).encode())
            return

        try:
            bot = Bot(token=BOT_TOKEN)
            result = asyncio.run(run_broadcast_batch(bot))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", **result}).encode())
        except Exception as e:
            logger.error(f"[v0] cron_broadcast error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

    def log_message(self, format, *args):
        logger.debug(f"[v0] cron_broadcast: {format % args}")


if __name__ == "__main__":
    from http.server import HTTPServer
    server = HTTPServer(("localhost", 3003), handler)
    print("[v0] cron_broadcast listening on http://localhost:3003")
    server.serve_forever()
