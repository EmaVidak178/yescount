"""Tests for monthly voting window helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from src.utils.voting_window import (
    VotingWindow,
    format_deadline_label,
    get_voting_target_month,
    get_voting_window,
    get_voting_window_close,
    get_voting_window_open,
)


def test_target_month_rolls_forward():
    assert get_voting_target_month(datetime(2026, 2, 15, tzinfo=UTC)) == (2026, 3)
    assert get_voting_target_month(datetime(2026, 12, 15, tzinfo=UTC)) == (2027, 1)


def test_window_open_uses_last_friday_of_month():
    # Feb 2026 last Friday is Feb 27.
    open_ts = get_voting_window_open(datetime(2026, 2, 1, tzinfo=UTC))
    assert open_ts == datetime(2026, 2, 27, 0, 0, 0, 0, tzinfo=UTC)


def test_window_close_is_first_day_of_next_month_end_of_day():
    close_ts = get_voting_window_close(datetime(2026, 2, 20, tzinfo=UTC))
    assert close_ts == datetime(2026, 3, 1, 23, 59, 59, 999999, tzinfo=UTC)


def test_format_deadline_label_contains_utc():
    label = format_deadline_label(datetime(2026, 3, 1, 23, 59, tzinfo=UTC))
    assert "UTC" in label


def test_get_voting_window_open_and_closed_states():
    open_state = get_voting_window(datetime(2026, 2, 28, 12, 0, 0, tzinfo=UTC))
    closed_state = get_voting_window(datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC))
    assert isinstance(open_state, VotingWindow)
    assert open_state.is_open is True
    assert closed_state.is_open is False


def test_target_month_december_rolls_to_january():
    """Dec -> vote for Jan next year."""
    assert get_voting_target_month(datetime(2025, 12, 15, tzinfo=UTC)) == (2026, 1)


def test_window_close_december_rolls_to_january():
    """Dec voting closes end-of-day Jan 1 next year."""
    close_ts = get_voting_window_close(datetime(2025, 12, 20, tzinfo=UTC))
    assert close_ts == datetime(2026, 1, 1, 23, 59, 59, 999999, tzinfo=UTC)


def test_window_boundary_at_open_and_close():
    """is_open True at exact open and just before close (close rolls to next target)."""
    # Feb 2026: last Friday is Feb 27, March window closes Mar 1 23:59:59.999999
    open_ts = get_voting_window_open(datetime(2026, 2, 1, tzinfo=UTC))
    at_open = get_voting_window(open_ts)
    assert at_open.is_open is True
    # Last moment still in Feb: Feb 28 23:59:59 is within March window
    last_moment_feb = datetime(2026, 2, 28, 23, 59, 59, 999999, tzinfo=UTC)
    still_open = get_voting_window(last_moment_feb)
    assert still_open.is_open is True


def test_window_closed_after_deadline():
    """is_open False when past close_utc."""
    # Feb voting closes Mar 1 23:59:59; Mar 2 00:00 is past deadline
    after_close = datetime(2026, 3, 2, 0, 0, 0, tzinfo=UTC)
    state = get_voting_window(after_close)
    assert state.is_open is False


def test_naive_datetime_handled():
    """Naive datetime (tzinfo=None) is treated as UTC."""
    naive = datetime(2026, 2, 28, 12, 0, 0)
    state = get_voting_window(naive)
    assert state.is_open is True
