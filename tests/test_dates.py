"""Tests du calcul d'anciennete et des dates (section 17)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.utils.dates import (
    compute_cutoff,
    is_older_than_cutoff,
    last_day_of_month,
    parse_gmail_date,
    subtract_months,
)

UTC = timezone.utc


def test_subtract_two_months_simple():
    moment = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    assert subtract_months(moment, 2) == datetime(2026, 4, 15, 12, 0, tzinfo=UTC)


def test_two_calendar_months_is_not_60_days():
    # Du 1 janvier au 1 mars : 59 jours en 2026 (non bissextile), pas 60.
    moment = datetime(2026, 3, 1, tzinfo=UTC)
    cutoff = subtract_months(moment, 2)
    assert cutoff == datetime(2026, 1, 1, tzinfo=UTC)
    assert (moment - cutoff).days == 59


def test_end_of_month_january_to_november():
    # 31 janvier moins 2 mois -> 30 novembre (novembre n'a pas de 31).
    moment = datetime(2026, 1, 31, tzinfo=UTC)
    assert subtract_months(moment, 2) == datetime(2025, 11, 30, tzinfo=UTC)


def test_end_of_month_march_to_january():
    moment = datetime(2026, 3, 31, tzinfo=UTC)
    assert subtract_months(moment, 2) == datetime(2026, 1, 31, tzinfo=UTC)


def test_leap_year_february():
    # 31 mars 2024 (bissextile) moins 2 mois -> 31 janvier 2024.
    assert last_day_of_month(2024, 2) == 29
    moment = datetime(2024, 3, 31, tzinfo=UTC)
    assert subtract_months(moment, 2) == datetime(2024, 1, 31, tzinfo=UTC)


def test_leap_day_february_29_kept():
    moment = datetime(2024, 2, 29, tzinfo=UTC)
    assert subtract_months(moment, 12) == datetime(2023, 2, 28, tzinfo=UTC)


def test_year_boundary():
    moment = datetime(2026, 1, 15, tzinfo=UTC)
    assert subtract_months(moment, 2) == datetime(2025, 11, 15, tzinfo=UTC)


def test_negative_months_rejected():
    with pytest.raises(ValueError):
        subtract_months(datetime(2026, 1, 1, tzinfo=UTC), -1)


def test_compute_cutoff_uses_timezone():
    now = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    cutoff = compute_cutoff(now, 2, "UTC")
    assert cutoff == datetime(2026, 4, 15, 12, 0, tzinfo=UTC)


def test_is_older_than_cutoff_strict():
    cutoff = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    older = datetime(2026, 4, 15, 11, 59, tzinfo=UTC)
    equal = cutoff
    newer = datetime(2026, 4, 15, 12, 1, tzinfo=UTC)
    assert is_older_than_cutoff(older, cutoff) is True
    assert is_older_than_cutoff(equal, cutoff) is False
    assert is_older_than_cutoff(newer, cutoff) is False


def test_is_older_than_cutoff_handles_none():
    cutoff = datetime(2026, 4, 15, tzinfo=UTC)
    assert is_older_than_cutoff(None, cutoff) is False


def test_parse_gmail_date_with_offset():
    parsed = parse_gmail_date("Mon, 15 Jun 2026 12:00:00 +0200", "UTC")
    assert parsed is not None
    assert parsed.astimezone(UTC).hour == 10


def test_parse_gmail_date_invalid():
    assert parse_gmail_date(None) is None
    assert parse_gmail_date("pas une date") is None
