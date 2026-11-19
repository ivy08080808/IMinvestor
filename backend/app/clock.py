"""Single source of "now" for the whole backend.

Every module must call :func:`now` instead of ``datetime.now()`` so that all
business time is Asia/Taipei wall-clock time. Tests may monkeypatch
``app.clock.now``.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.constants import TIMEZONE

TZ = ZoneInfo(TIMEZONE)


def now() -> datetime:
    """Return the current Asia/Taipei time as a naive datetime.

    Naive values match the ``timestamp`` (without time zone) columns in the schema.
    """
    return datetime.now(TZ).replace(tzinfo=None)


def today() -> date:
    """Return today's date in Asia/Taipei."""
    return now().date()
