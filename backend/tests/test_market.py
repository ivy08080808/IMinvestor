"""Phase / belong-date boundaries (plan §4.2). Uses a rolled-back DB transaction."""

from __future__ import annotations

from datetime import date, datetime

import psycopg
import pytest

from app import market
from app.errors import AppError

THU = date(2031, 1, 2)   # far-future dates so real data never collides
FRI = date(2031, 1, 3)
SAT = date(2031, 1, 4)
SUN = date(2031, 1, 5)
MON = date(2031, 1, 6)


@pytest.fixture
def cal(conn: psycopg.Connection) -> psycopg.Connection:
    for d, trading in [(THU, True), (FRI, True), (SAT, False), (SUN, False), (MON, True)]:
        conn.execute(
            "INSERT INTO trading_calendar VALUES (%s, %s) ON CONFLICT DO NOTHING", (d, trading)
        )
    return conn


def at(d: date, hh: int, mm: int = 0, ss: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, ss)


def test_phases_on_trading_day(cal: psycopg.Connection) -> None:
    assert market.phase_at(cal, at(THU, 8, 59)) == market.PRE_OPEN
    assert market.phase_at(cal, at(THU, 9, 0)) == market.OPEN
    assert market.phase_at(cal, at(THU, 13, 30)) == market.CLOSED
    assert market.phase_at(cal, at(THU, 15, 0)) == market.SETTLING


def test_belong_date_before_and_at_cutoff(cal: psycopg.Connection) -> None:
    assert market.order_belong_date(cal, at(THU, 14, 59, 59)) == THU
    with pytest.raises(AppError) as exc:
        market.order_belong_date(cal, at(THU, 15, 0, 0))
    assert exc.value.code == "SETTLING"


def test_after_settlement_goes_to_next_trading_day(cal: psycopg.Connection) -> None:
    cal.execute(
        "INSERT INTO settlement_run (trade_date, status, started_at) VALUES (%s, '完成', %s)",
        (FRI, at(FRI, 15, 0)),
    )
    assert market.phase_at(cal, at(FRI, 15, 1)) == market.SETTLED
    assert market.order_belong_date(cal, at(FRI, 15, 1)) == MON     # skips the weekend


def test_weekend_belongs_to_monday(cal: psycopg.Connection) -> None:
    assert market.phase_at(cal, at(SAT, 10)) == market.HOLIDAY
    assert market.order_belong_date(cal, at(SUN, 23, 59)) == MON
