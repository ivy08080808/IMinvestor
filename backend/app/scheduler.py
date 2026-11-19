"""Background scheduler (framework-owned, implemented).

Runs inside the FastAPI process. Start only ONE backend process with
``SCHEDULER_ENABLED=1``; extra copies (e.g. a second instance for testing)
should set it to 0. Even if two run, SETTLEMENT_RUN's claim keeps the daily
job exactly-once.
"""

from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import jobs
from app.constants import TIMEZONE
from app.db import connection
from app.errors import NotImplementedYet
from crawler import holidays, securities

log = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def _sync_securities_job() -> None:
    try:
        with connection() as conn:
            n = securities.sync_securities(conn)
        log.info("security list synced: %s new", n)
    except NotImplementedYet as exc:
        log.warning(exc.message)


def _sync_holidays_job() -> None:
    try:
        with connection() as conn:
            n = holidays.sync_holidays(conn)
        log.info("holidays synced: %s rows", n)
    except NotImplementedYet as exc:
        log.warning(exc.message)


def start() -> None:
    """Start cron jobs and run the startup catch-up in the background."""
    global _scheduler
    if _scheduler is not None:
        return
    sched = BackgroundScheduler(timezone=TIMEZONE)
    # The one daily fetch + settlement (plan v2: fully automatic, 15:00 only).
    sched.add_job(jobs.daily_job, CronTrigger(day_of_week="mon-fri", hour=15, minute=0,
                                              timezone=TIMEZONE),
                  id="daily_import_and_settle", max_instances=1, coalesce=True,
                  misfire_grace_time=3600)
    sched.add_job(_sync_securities_job, CronTrigger(hour=6, minute=0, timezone=TIMEZONE),
                  id="sync_securities", max_instances=1, coalesce=True)
    sched.add_job(_sync_holidays_job, CronTrigger(day_of_week="mon", hour=6, minute=10,
                                                  timezone=TIMEZONE),
                  id="sync_holidays", max_instances=1, coalesce=True)
    sched.add_job(jobs.catch_up, id="startup_catch_up")      # runs once, immediately
    sched.start()
    _scheduler = sched
    log.info("scheduler started")


def shutdown() -> None:
    """Stop the scheduler on application shutdown."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
