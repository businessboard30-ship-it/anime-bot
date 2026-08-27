"""
Shared broadcast batch-processing logic.

This used to only live in api/cron_broadcast.py, driven by a scheduled cron
hit. That required either Vercel Pro (per-minute cron) or an external
scheduler — infrastructure L,kl doesn't want. Instead, batches are now driven
manually: the admin taps "Send Next Batch" in Telegram whenever they want the
broadcast to keep moving, right after /broadcast confirm and again from
/broadcast_status any time later. No scheduler, no cron, no timers — the
admin decides when it posts by tapping a button.

api/cron_broadcast.py still exists and calls run_broadcast_batch() too, in
case you ever DO want to wire up a cron or external scheduler later — but
nothing requires it anymore.
"""
import logging

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from database import db
from handlers.premium_group_handler import premium_group_button

logger = logging.getLogger(__name__)

BATCH_LIMIT = 20  # keep each manual tap well under Vercel's maxDuration

# Every outbound broadcast carries this footer. A fixed-price Premium Group
# paywall button is always added (below) and an optional admin-assigned
# "Join Group/Channel" button (only if that specific job set one — see
# handlers/broadcast_handler.py's join-link step).


def _broadcast_keyboard(job: dict) -> InlineKeyboardMarkup:
    rows = [
        [premium_group_button()],
    ]
    join_link = job.get("join_link")
    if join_link:
        rows.append([InlineKeyboardButton("📢 Join Our Group/Channel", url=join_link)])
    return InlineKeyboardMarkup(rows)


async def _send_broadcast(bot: Bot, job: dict, chat_id: int):
    content = job.get("content")
    media_type = job.get("media_type")
    media_file_id = job.get("media_file_id")
    caption = content if content else None
    keyboard = _broadcast_keyboard(job)

    if media_type == "photo":
        await bot.send_photo(chat_id=chat_id, photo=media_file_id, caption=caption, reply_markup=keyboard)
    elif media_type == "video":
        await bot.send_video(chat_id=chat_id, video=media_file_id, caption=caption, reply_markup=keyboard)
    elif media_type == "animation":
        await bot.send_animation(chat_id=chat_id, animation=media_file_id, caption=caption, reply_markup=keyboard)
    elif media_type == "document":
        await bot.send_document(chat_id=chat_id, document=media_file_id, caption=caption, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id=chat_id, text=caption or "", reply_markup=keyboard)


async def run_broadcast_batch(bot: Bot, job_id: int = None, batch_size: int = BATCH_LIMIT) -> dict:
    """
    Process one batch of the given job (or the oldest pending/in_progress job
    if job_id is None). Returns a dict with job_id, processed, sent, failed,
    job_status ("pending" | "in_progress" | "done" | "none_pending").
    """
    if job_id is None:
        job = await db.get_next_broadcast_job()
    else:
        job = await db.get_broadcast_job(job_id)

    if not job:
        return {"job_id": job_id, "processed": 0, "sent": 0, "failed": 0, "job_status": "none_pending"}

    batch = await db.get_broadcast_batch(job["id"], batch_size=batch_size)

    sent, failed = 0, 0
    for recipient in batch:
        try:
            await _send_broadcast(bot, job, recipient["chat_id"])
            await db.mark_broadcast_recipient(recipient["id"], error=None)
            sent += 1
        except TelegramError as e:
            await db.mark_broadcast_recipient(recipient["id"], error=str(e))
            failed += 1
        except Exception as e:
            await db.mark_broadcast_recipient(recipient["id"], error=str(e))
            failed += 1

    status = await db.finalize_broadcast_job_progress(job["id"])
    return {"job_id": job["id"], "processed": len(batch), "sent": sent, "failed": failed, "job_status": status}
