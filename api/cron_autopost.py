"""
Cron-triggered endpoint for autopost (recurring posts).

This deployment is a stateless Vercel webhook with no long-running process,
so there is no in-process scheduler loop (unlike superbot.py's original
recurring_post_job). Instead, an external scheduler hits this endpoint on a
schedule and each invocation sends whatever recurring posts are currently due.

Auth: either header "Authorization: Bearer <CRON_SECRET>" (what Vercel Cron
sends automatically when the CRON_SECRET env var is set) or query param
?secret=<CRON_SECRET> (for external pingers like cron-job.org or a GitHub
Actions scheduled workflow, which is required if you're on Vercel's Hobby
plan — see the note in vercel.json about its once-per-day cron floor).
"""
import json
import asyncio
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from config import BOT_TOKEN, CRON_SECRET
from database import db

logger = logging.getLogger(__name__)

BATCH_LIMIT = 20  # keep each invocation well under Vercel's maxDuration


class handler(BaseHTTPRequestHandler):

    def _authorized(self) -> bool:
        if not CRON_SECRET:
            # No secret configured — refuse rather than run wide open.
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
            result = asyncio.run(_run_cron_cycle())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", **result}).encode())
        except Exception as e:
            logger.error(f"[v0] cron_autopost error: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

    def log_message(self, format, *args):
        logger.debug(f"[v0] cron_autopost: {format % args}")


async def _run_cron_cycle() -> dict:
    """Single entrypoint for this cron invocation: process due recurring posts,
    then check for a sponsored post to inject, sharing one Bot instance."""
    bot = Bot(token=BOT_TOKEN)
    result = await _run_due_autoposts(bot)
    sponsored_result = await _send_sponsored_if_due(bot)
    result.update(sponsored_result)
    return result


async def _run_due_autoposts(bot: Bot) -> dict:
    due = await db.get_due_recurring_posts(limit=BATCH_LIMIT)

    sent, failed = 0, 0
    errors = []

    for post in due:
        try:
            await _send_post(bot, post)
            await db.mark_recurring_posted(post["id"])
            sent += 1
        except TelegramError as e:
            failure_count = await db.bump_recurring_failure(post["id"])
            failed += 1
            errors.append({"id": post["id"], "chat_id": post["chat_id"], "error": str(e), "failure_count": failure_count})
        except Exception as e:
            failed += 1
            errors.append({"id": post["id"], "chat_id": post["chat_id"], "error": str(e)})

    return {"processed": len(due), "sent": sent, "failed": failed, "errors": errors}


async def _send_sponsored_if_due(bot: Bot) -> dict:
    """Ported from SUPER-BOT's get_next_sponsored/mark_sponsored_sent: once per
    cron invocation (not once per chat), check for a queued sponsored post and
    if one exists with runs remaining, send it to every known chat and mark it
    sent exactly once for this cycle."""
    sponsored = await db.get_next_sponsored()
    if not sponsored:
        return {"sponsored_sent": False}

    chat_ids = await db.get_autopost_chat_ids()
    keyboard = None
    if sponsored.get("button_label") and sponsored.get("button_url"):
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(sponsored["button_label"], url=sponsored["button_url"])
        ]])

    sent, failed = 0, 0
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=sponsored["content"], reply_markup=keyboard)
            sent += 1
        except TelegramError as e:
            failed += 1
            logger.warning(f"[v0] Sponsored post send failed for chat {chat_id}: {e}")

    await db.mark_sponsored_sent(sponsored["id"])
    return {"sponsored_sent": True, "sponsored_id": sponsored["id"], "sponsored_chats_sent": sent, "sponsored_chats_failed": failed}


async def _send_post(bot: Bot, post: dict):
    chat_id = post["chat_id"]
    content = post.get("content")
    media_type = post.get("media_type")
    media_file_id = post.get("media_file_id")

    if media_type == "photo":
        await bot.send_photo(chat_id=chat_id, photo=media_file_id, caption=content)
    elif media_type == "video":
        await bot.send_video(chat_id=chat_id, video=media_file_id, caption=content)
    elif media_type == "animation":
        await bot.send_animation(chat_id=chat_id, animation=media_file_id, caption=content)
    elif media_type == "document":
        await bot.send_document(chat_id=chat_id, document=media_file_id, caption=content)
    else:
        await bot.send_message(chat_id=chat_id, text=content or "")


if __name__ == "__main__":
    from http.server import HTTPServer
    server = HTTPServer(("localhost", 3002), handler)
    print("[v0] cron_autopost listening on http://localhost:3002")
    server.serve_forever()
