"""Tests du service de scan (lecture seule)."""

from __future__ import annotations

from datetime import datetime, timezone

from src.ai.classifier import RuleBasedClassifier
from src.core.models import EmailMessage, ProtectionStatus, Recommendation
from src.gmail.email_repository import SearchScope, build_query
from src.gmail.fake_client import FakeGmailClient
from src.services.protection_service import ProtectionService
from src.services.scan_service import ScanService

UTC = timezone.utc
CUTOFF = datetime(2026, 4, 15, tzinfo=UTC)


def _message(mid, when, labels, subject="Sujet", sender_email="a@b.com"):
    return EmailMessage(
        id=mid,
        thread_id=f"t-{mid}",
        subject=subject,
        sender=f"N <{sender_email}>" if sender_email else "Inconnu",
        sender_email=sender_email,
        date=when,
        label_ids=tuple(labels),
        is_starred="STARRED" in labels,
        is_in_inbox="INBOX" in labels,
        is_in_trash="TRASH" in labels,
        is_in_spam="SPAM" in labels,
        snippet="publicite promo",
    )


def _service(client, protected=None):
    return ScanService(
        client=client,
        classifier=RuleBasedClassifier(),
        protection=ProtectionService(protected_emails=protected or set()),
        tz_name="UTC",
    )


def test_scan_counts_old_vs_recent():
    old = datetime(2025, 1, 1, tzinfo=UTC)
    recent = datetime(2026, 6, 1, tzinfo=UTC)
    client = FakeGmailClient(
        [
            _message("old1", old, ["INBOX"]),
            _message("recent1", recent, ["INBOX"]),
        ],
        page_size=1,
    )
    result = _service(client).scan(build_query([SearchScope.INBOX], CUTOFF))
    assert result.fetched == 2
    assert result.analyzed == 1
    assert result.excluded == 1
    assert result.candidate_count == 1
    assert result.candidates[0].message.id == "old1"


def test_scan_protects_starred_and_contacts():
    old = datetime(2025, 1, 1, tzinfo=UTC)
    client = FakeGmailClient(
        [
            _message("starred", old, ["INBOX", "STARRED"]),
            _message("contact", old, ["INBOX"], sender_email="vip@example.com"),
            _message("normal", old, ["INBOX"]),
        ]
    )
    result = _service(client, protected={"vip@example.com"}).scan(
        build_query([SearchScope.INBOX], CUTOFF)
    )
    assert result.analyzed == 3
    assert result.protected == 2
    statuses = {c.message.id: c.protection for c in result.candidates}
    assert statuses["starred"] == ProtectionStatus.PROTECTED_STAR
    assert statuses["contact"] == ProtectionStatus.PROTECTED_SENDER
    assert statuses["normal"] == ProtectionStatus.NOT_PROTECTED


def test_scan_never_preselects():
    old = datetime(2025, 1, 1, tzinfo=UTC)
    client = FakeGmailClient([_message("m1", old, ["INBOX"])])
    result = _service(client).scan(build_query([SearchScope.INBOX], CUTOFF))
    assert all(candidate.selected is False for candidate in result.candidates)


def test_scan_excludes_trash_and_spam():
    old = datetime(2025, 1, 1, tzinfo=UTC)
    client = FakeGmailClient(
        [
            _message("trash", old, ["TRASH"]),
            _message("spam", old, ["SPAM"]),
            _message("inbox", old, ["INBOX"]),
        ]
    )
    result = _service(client).scan(build_query([SearchScope.ALL_MAIL], CUTOFF))
    ids = {c.message.id for c in result.candidates if c.protection == ProtectionStatus.NOT_PROTECTED}
    assert ids == {"inbox"}


def test_scan_classifies_eligible_messages():
    old = datetime(2025, 1, 1, tzinfo=UTC)
    client = FakeGmailClient([_message("m1", old, ["INBOX"])])
    result = _service(client).scan(build_query([SearchScope.INBOX], CUTOFF))
    candidate = result.candidates[0]
    assert candidate.classification is not None
    assert candidate.classification.recommendation in set(Recommendation)
    assert candidate.is_eligible is True


def test_scan_handles_client_error():
    class _FailingClient:
        def iter_message_ids(self, query):
            raise RuntimeError("API indisponible")

    result = _service(_FailingClient()).scan(build_query([SearchScope.INBOX], CUTOFF))
    assert result.candidate_count == 0
    assert result.errors
