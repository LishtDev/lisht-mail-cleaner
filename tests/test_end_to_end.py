"""Test de bout en bout avec le faux client Gmail.

Parcours complet : scan -> selection -> mise en corbeille, sans compte reel.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.ai.classifier import RuleBasedClassifier
from src.core.models import EmailMessage
from src.gmail.email_repository import SearchScope, build_query
from src.gmail.fake_client import FakeGmailClient
from src.services.cleanup_service import CleanupMode, CleanupService, Confirmation
from src.services.protection_service import ProtectionService
from src.services.scan_service import ScanService

UTC = timezone.utc
CUTOFF = datetime(2026, 4, 15, tzinfo=UTC)


def _message(mid, when, labels, sender_email="a@b.com", snippet="publicite promo"):
    return EmailMessage(
        id=mid,
        subject="Promo",
        sender=f"N <{sender_email}>",
        sender_email=sender_email,
        date=when,
        label_ids=tuple(labels),
        is_starred="STARRED" in labels,
        is_in_inbox="INBOX" in labels,
        snippet=snippet,
    )


def test_end_to_end_scan_then_trash():
    old = datetime(2025, 1, 1, tzinfo=UTC)
    client = FakeGmailClient(
        [
            _message("m1", old, ["INBOX"]),
            _message("m2", old, ["INBOX", "STARRED"]),
            _message("m3", old, ["INBOX"], sender_email="vip@example.com"),
        ]
    )
    protection = ProtectionService(protected_emails={"vip@example.com"})
    scan = ScanService(client, RuleBasedClassifier(), protection, tz_name="UTC")
    result = scan.scan(build_query([SearchScope.INBOX], CUTOFF))

    eligible = [c for c in result.candidates if c.is_eligible]
    assert [c.message.id for c in eligible] == ["m1"]

    for candidate in eligible:
        candidate.selected = True

    cleanup = CleanupService(client, protection, max_delete=10, dry_run=False)
    confirmation = Confirmation(
        mode=CleanupMode.TRASH,
        confirmed_count=1,
        human_validated=True,
        dry_run=False,
    )
    outcome = cleanup.execute(eligible, CleanupMode.TRASH, confirmation, cutoff=CUTOFF)
    assert outcome.trashed == 1
    assert client.trashed == ["m1"]
    assert client.deleted == []
