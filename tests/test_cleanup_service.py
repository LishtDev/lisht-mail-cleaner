"""Tests du service de nettoyage : confirmations, limites, protections.

Ces tests n'effectuent AUCUNE suppression reelle : ils utilisent le faux
client Gmail.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.models import Candidate, Category, Classification, EmailMessage, ProtectionStatus, Recommendation
from src.gmail.fake_client import FakeGmailClient
from src.services.cleanup_service import (
    REQUIRED_DELETE_PHRASE,
    CleanupError,
    CleanupMode,
    CleanupService,
    Confirmation,
    LimitExceededError,
)
from src.services.protection_service import ProtectionService

UTC = timezone.utc
CUTOFF = datetime(2026, 4, 15, tzinfo=UTC)


def _message(mid, when=None, labels=None, sender_email="a@b.com"):
    labels = labels or ["INBOX"]
    return EmailMessage(
        id=mid,
        subject="Sujet",
        sender=f"N <{sender_email}>",
        sender_email=sender_email,
        date=when or datetime(2025, 1, 1, tzinfo=UTC),
        label_ids=tuple(labels),
        is_starred="STARRED" in labels,
        is_in_inbox="INBOX" in labels,
    )


def _candidate(mid, when=None, sender_email="a@b.com"):
    return Candidate(
        message=_message(mid, when, sender_email=sender_email),
        classification=Classification(
            category=Category.ADVERTISING,
            recommendation=Recommendation.DELETE_CANDIDATE,
            confidence=0.8,
        ),
        protection=ProtectionStatus.NOT_PROTECTED,
        selected=True,
    )


def _service(client, protected=None, dry_run=False, max_delete=50):
    return CleanupService(
        client=client,
        protection=ProtectionService(protected_emails=protected or set()),
        max_delete=max_delete,
        dry_run=dry_run,
    )


def _confirm(mode, count, phrase="", dry_run=False):
    return Confirmation(
        mode=mode,
        confirmed_count=count,
        phrase=phrase,
        human_validated=True,
        dry_run=dry_run,
    )


def test_dry_run_never_calls_delete():
    client = FakeGmailClient([_message("m1")])
    service = _service(client, dry_run=True)
    result = service.execute(
        [_candidate("m1")],
        CleanupMode.DELETE,
        _confirm(CleanupMode.DELETE, 1, REQUIRED_DELETE_PHRASE, dry_run=True),
        cutoff=CUTOFF,
    )
    assert result.dry_run is True
    assert client.deleted == []


def test_delete_without_phrase_refused():
    client = FakeGmailClient([_message("m1")])
    service = _service(client, dry_run=False)
    with pytest.raises(CleanupError):
        service.execute(
            [_candidate("m1")],
            CleanupMode.DELETE,
            _confirm(CleanupMode.DELETE, 1, phrase="", dry_run=False),
            cutoff=CUTOFF,
        )
    assert client.deleted == []


def test_delete_without_human_validation_refused():
    client = FakeGmailClient([_message("m1")])
    service = _service(client, dry_run=False)
    bad = Confirmation(
        mode=CleanupMode.DELETE,
        confirmed_count=1,
        phrase=REQUIRED_DELETE_PHRASE,
        human_validated=False,
        dry_run=False,
    )
    with pytest.raises(CleanupError):
        service.execute([_candidate("m1")], CleanupMode.DELETE, bad, cutoff=CUTOFF)
    assert client.deleted == []


def test_delete_count_mismatch_refused():
    client = FakeGmailClient([_message("m1"), _message("m2")])
    service = _service(client, dry_run=False)
    with pytest.raises(CleanupError):
        service.execute(
            [_candidate("m1"), _candidate("m2")],
            CleanupMode.DELETE,
            _confirm(CleanupMode.DELETE, 1, REQUIRED_DELETE_PHRASE, dry_run=False),
            cutoff=CUTOFF,
        )
    assert client.deleted == []


def test_delete_with_valid_confirmation_executes():
    client = FakeGmailClient([_message("m1")])
    service = _service(client, dry_run=False)
    result = service.execute(
        [_candidate("m1")],
        CleanupMode.DELETE,
        _confirm(CleanupMode.DELETE, 1, REQUIRED_DELETE_PHRASE, dry_run=False),
        cutoff=CUTOFF,
    )
    assert result.deleted == 1
    assert client.deleted == ["m1"]


def test_trash_does_not_require_phrase():
    client = FakeGmailClient([_message("m1")])
    service = _service(client, dry_run=False)
    result = service.execute(
        [_candidate("m1")],
        CleanupMode.TRASH,
        _confirm(CleanupMode.TRASH, 1, dry_run=False),
        cutoff=CUTOFF,
    )
    assert result.trashed == 1
    assert client.trashed == ["m1"]
    assert client.deleted == []


def test_limit_exceeded_refused():
    client = FakeGmailClient([_message(f"m{i}") for i in range(5)])
    service = _service(client, dry_run=False, max_delete=2)
    with pytest.raises(LimitExceededError):
        service.execute(
            [_candidate(f"m{i}") for i in range(5)],
            CleanupMode.DELETE,
            _confirm(CleanupMode.DELETE, 5, REQUIRED_DELETE_PHRASE, dry_run=False),
            cutoff=CUTOFF,
        )
    assert client.deleted == []


def test_revalidation_skips_now_protected():
    # Le message est etoile au moment de l'action -> doit etre ecarte.
    client = FakeGmailClient([_message("m1", labels=["INBOX", "STARRED"])])
    service = _service(client, dry_run=False)
    result = service.execute(
        [_candidate("m1")],
        CleanupMode.TRASH,
        _confirm(CleanupMode.TRASH, 1, dry_run=False),
        cutoff=CUTOFF,
    )
    assert result.trashed == 0
    assert result.skipped == 1
    assert client.trashed == []


def test_revalidation_skips_missing_message():
    client = FakeGmailClient([_message("m2")])
    service = _service(client, dry_run=False)
    result = service.execute(
        [_candidate("m1")],
        CleanupMode.TRASH,
        _confirm(CleanupMode.TRASH, 1, dry_run=False),
        cutoff=CUTOFF,
    )
    assert result.trashed == 0
    assert result.skipped == 1


def test_revalidation_skips_now_recent():
    recent = datetime(2026, 6, 1, tzinfo=UTC)
    client = FakeGmailClient([_message("m1", when=recent)])
    service = _service(client, dry_run=False)
    result = service.execute(
        [_candidate("m1", when=recent)],
        CleanupMode.TRASH,
        _confirm(CleanupMode.TRASH, 1, dry_run=False),
        cutoff=CUTOFF,
    )
    assert result.trashed == 0
    assert result.skipped == 1


def test_empty_selection_returns_early():
    client = FakeGmailClient([])
    service = _service(client)
    result = service.execute([], CleanupMode.TRASH, _confirm(CleanupMode.TRASH, 0))
    assert result.trashed == 0 and result.deleted == 0
