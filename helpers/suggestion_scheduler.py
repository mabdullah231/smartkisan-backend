"""
APScheduler: run suggestion generation 4× daily (Asia/Karachi default).
Disable with env SUGGESTION_CRON_DISABLED=1
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


def start_suggestion_scheduler() -> Optional[AsyncIOScheduler]:
    global _scheduler
    if os.getenv("SUGGESTION_CRON_DISABLED", "").lower() in ("1", "true", "yes"):
        logger.info("Suggestion scheduler disabled (SUGGESTION_CRON_DISABLED)")
        return None

    tz_name = os.getenv("SUGGESTION_TIMEZONE", "Asia/Karachi")
    tz = ZoneInfo(tz_name)
    _scheduler = AsyncIOScheduler(timezone=tz)

    from helpers.suggestion_generator import run_suggestion_job_for_all_users

    async def job():
        try:
            await run_suggestion_job_for_all_users()
        except Exception:
            logger.exception("Scheduled suggestion job failed")

    for hour in (0, 6, 12, 18):
        _scheduler.add_job(
            job,
            "cron",
            hour=hour,
            minute=0,
            id=f"suggestion_gen_{hour}h",
            replace_existing=True,
        )

    _scheduler.start()
    logger.info(
        "Suggestion scheduler started: 00:00, 06:00, 12:00, 18:00 (%s)",
        tz_name,
    )
    return _scheduler


def shutdown_suggestion_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Suggestion scheduler stopped")
