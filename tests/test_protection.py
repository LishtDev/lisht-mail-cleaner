"""Tests des regles de protection (section 9)."""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.models import EmailMessage, ProtectionStatus
from src.services.protection_service import ProtectionService

UTC = timezone.utc


def _message(starred=False, sender_email="ami@example.com"):
    return EmailMessage(
        id="m1",
        sender=f"Quelqu'un <{sender_email}>" if sender_email else "Inconnu",
        sender_email=sender_email,
        date=datetime(2025, 1, 1, tzinfo=UTC),
        label_ids=("STARRED",) if starred else (),
        is_starred=starred,
    )


def test_starred_is_protected():
    service = ProtectionService()
    assert service.evaluate(_message(starred=True)) == ProtectionStatus.PROTECTED_STAR


def test_protected_contact():
    service = ProtectionService(protected_emails={"ami@example.com"})
    assert service.evaluate(_message()) == ProtectionStatus.PROTECTED_SENDER


def test_uncertain_sender_is_protected():
    service = ProtectionService()
    assert service.evaluate(_message(sender_email="")) == ProtectionStatus.PROTECTED_UNCERTAIN


def test_not_protected_normal_message():
    service = ProtectionService()
    assert service.evaluate(_message()) == ProtectionStatus.NOT_PROTECTED


def test_not_analyzed_status():
    service = ProtectionService()
    assert service.evaluate(_message(), analyzed=False) == ProtectionStatus.NOT_ANALYZED


def test_star_takes_precedence_over_contact():
    service = ProtectionService(protected_emails={"ami@example.com"})
    assert service.evaluate(_message(starred=True)) == ProtectionStatus.PROTECTED_STAR


def test_is_protected_helper():
    assert ProtectionService.is_protected(ProtectionStatus.PROTECTED_STAR) is True
    assert ProtectionService.is_protected(ProtectionStatus.NOT_PROTECTED) is False


def test_case_insensitive_contact_match():
    service = ProtectionService(protected_emails={"Ami@Example.COM"})
    assert service.evaluate(_message(sender_email="ami@example.com")) == (
        ProtectionStatus.PROTECTED_SENDER
    )
