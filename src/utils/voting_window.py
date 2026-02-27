"""Monthly voting window helpers.

Voting window policy:
- Opens on Friday of the last week of the month.
- Closes at end-of-day on the 1st day of the following month.
- Voting target is the following month (e.g. open in late Feb -> vote for March).

All inputs and outputs use UTC.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class VotingWindow:
    """Voting window for a target month."""

    target_year: int
    target_month: int
    open_utc: datetime
    close_utc: datetime
    deadline_label: str
    is_open: bool


def get_voting_target_month(utc_now: datetime) -> tuple[int, int]:
    """Return (year, month) for the month being voted for.

    Voting is for the month following the current month. E.g., in Feb 2026
    we vote for March 2026.
    """
    if utc_now.tzinfo is None:
        utc_now = utc_now.replace(tzinfo=UTC)
    year, month = utc_now.year, utc_now.month
    if month == 12:
        return (year + 1, 1)
    return (year, month + 1)


def _last_friday_of_month(year: int, month: int) -> int:
    """Return day-of-month number for the final Friday of a given month."""
    if month == 12:
        next_month_first = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        next_month_first = datetime(year, month + 1, 1, tzinfo=UTC)
    last_day = next_month_first - timedelta(days=1)
    # weekday(): Monday=0 ... Sunday=6. Friday=4.
    offset = (last_day.weekday() - 4) % 7
    return last_day.day - offset


def get_voting_window_open(utc_now: datetime) -> datetime:
    """Return UTC timestamp when this month's voting window opens."""
    if utc_now.tzinfo is None:
        utc_now = utc_now.replace(tzinfo=UTC)
    day = _last_friday_of_month(utc_now.year, utc_now.month)
    return datetime(utc_now.year, utc_now.month, day, 0, 0, 0, 0, tzinfo=UTC)


def get_voting_window_close(utc_now: datetime) -> datetime:
    """Return UTC timestamp when this month's voting window closes."""
    if utc_now.tzinfo is None:
        utc_now = utc_now.replace(tzinfo=UTC)
    if utc_now.month == 12:
        return datetime(utc_now.year + 1, 1, 1, 23, 59, 59, 999999, tzinfo=UTC)
    return datetime(utc_now.year, utc_now.month + 1, 1, 23, 59, 59, 999999, tzinfo=UTC)


def format_deadline_label(close_utc: datetime) -> str:
    """Return a user-facing deadline string, e.g. 'Feb 28, 11:59 PM UTC'."""
    return close_utc.strftime("%b %d, %I:%M %p UTC").replace(" 0", " ")


def get_voting_window(utc_now: datetime) -> VotingWindow:
    """Return the full voting window for the current target month."""
    target_year, target_month = get_voting_target_month(utc_now)
    open_utc = get_voting_window_open(utc_now)
    close_utc = get_voting_window_close(utc_now)
    month_name = datetime(target_year, target_month, 1).strftime("%B %Y")
    deadline_label = f"{month_name} voting closes {format_deadline_label(close_utc)}"
    if utc_now.tzinfo is None:
        utc_now = utc_now.replace(tzinfo=UTC)
    is_open = open_utc <= utc_now <= close_utc
    return VotingWindow(
        target_year=target_year,
        target_month=target_month,
        open_utc=open_utc,
        close_utc=close_utc,
        deadline_label=deadline_label,
        is_open=is_open,
    )
