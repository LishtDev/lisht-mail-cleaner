"""Tests du tableau de selection (interface, hors ecran)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from PySide6.QtCore import Qt

from src.core.models import (
    Candidate,
    Category,
    Classification,
    EmailMessage,
    ProtectionStatus,
    Recommendation,
)
from src.ui.email_table import EmailTableWidget

UTC = timezone.utc


def _candidate(mid, category, recommendation, protection=ProtectionStatus.NOT_PROTECTED, subject="Sujet"):
    message = EmailMessage(
        id=mid,
        subject=subject,
        sender="N <a@b.com>",
        sender_email="a@b.com",
        date=datetime(2025, 1, 1, tzinfo=UTC),
        is_starred=protection == ProtectionStatus.PROTECTED_STAR,
    )
    classification = None
    if protection == ProtectionStatus.NOT_PROTECTED:
        classification = Classification(
            category=category,
            justification="test",
            confidence=0.7,
            recommendation=recommendation,
            caution=False,
            source="rules",
        )
    return Candidate(message=message, classification=classification, protection=protection)


@pytest.fixture()
def table(qtbot):
    widget = EmailTableWidget("UTC")
    qtbot.addWidget(widget)
    return widget


def test_no_preselection(table):
    candidates = [_candidate("m1", Category.ADVERTISING, Recommendation.DELETE_CANDIDATE)]
    table.set_candidates(candidates)
    assert table.selected_candidates() == []


def test_check_all_selects_only_eligible(table):
    candidates = [
        _candidate("m1", Category.ADVERTISING, Recommendation.DELETE_CANDIDATE),
        _candidate("m2", Category.PERSONAL, Recommendation.REVIEW, ProtectionStatus.PROTECTED_STAR),
    ]
    table.set_candidates(candidates)
    table.check_all(True)
    selected = table.selected_candidates()
    assert [c.message.id for c in selected] == ["m1"]


def test_protected_row_not_checkable(table):
    candidates = [
        _candidate("m1", Category.PERSONAL, Recommendation.REVIEW, ProtectionStatus.PROTECTED_STAR)
    ]
    table.set_candidates(candidates)
    item = table.item(0, 0)
    assert not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable)


def test_filter_by_gategory(table):
    candidates = [
        _candidate("m1", Category.ADVERTISING, Recommendation.DELETE_CANDIDATE),
        _candidate("m2", Category.PERSONAL, Recommendation.REVIEW),
    ]
    table.set_candidates(candidates)
    visible = table.apply_filters(category="Publicite / promotion")
    assert visible == 1


def test_filter_only_candidates(table):
    candidates = [
        _candidate("m1", Category.ADVERTISING, Recommendation.DELETE_CANDIDATE),
        _candidate("m2", Category.PERSONAL, Recommendation.REVIEW),
    ]
    table.set_candidates(candidates)
    visible = table.apply_filters(only_candidates=True)
    assert visible == 1


def test_filter_by_search(table):
    candidates = [
        _candidate("m1", Category.ADVERTISING, Recommendation.DELETE_CANDIDATE, subject="Facture"),
        _candidate("m2", Category.ADVERTISING, Recommendation.DELETE_CANDIDATE, subject="Promo"),
    ]
    table.set_candidates(candidates)
    visible = table.apply_filters(search="facture")
    assert visible == 1
