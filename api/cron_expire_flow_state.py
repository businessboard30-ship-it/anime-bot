"""
Cron-triggered endpoint that sweeps abandoned multi-step "wizard" flows
out of user_flow_state (see database.py / flow_state.py) — broadcast,
autopost, clone customization, bot manager, ads marketplace, botstore,
games, crypto alerts, etc.

Reads already self-expire (get_user_flow_state ignores + deletes rows
older than db.USER_FLOW_STATE_TTL), so this job isn't required for
correctness — it just reclaims rows for users who abandoned a wizard
and never sent another message, instead of leaving them until their
next unrelated interaction happens to trigger the lazy check.

Auth: same pattern as api/cron_autopost.py / api/cron_broadcast.py /
api/cron_expire_monetization.py — either header
"Authorization: Bearer <CRON_SECRET>" (what Vercel Cron sends
automatically when CRON_SECRET is set) or query param ?secret=<CRON_SECRET>.
Run this once a day; expiry granularity doesn't need finer than that.
"""
import json
import asyncio
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from config import CRON_SECRET
from database import db

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
            result = asyncio.run(db.cleanup_expired_flow_state())
            logger.info(f"[v0] cron_expire_flow_state result={result}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "result": str(result)}).encode())
        except Exception as e:
            logger.error(f"[v0] cron_expire_flow_state error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

    def log_message(self, format, *args):
        logger.debug(f"[v0] cron_expire_flow_state: {format % args}")


if __name__ == '__main__':
    print(asyncio.run(db.cleanup_expired_flow_state()))
