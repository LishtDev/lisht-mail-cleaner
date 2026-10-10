"""Tests de la lecture Gmail : requetes, analyse des metadonnees, pagination."""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.models import EmailMessage
from src.gmail.email_repository import (
    SearchScope,
    build_query,
    parse_message_metadata,
)
from src.gmail.fake_client import FakeGmailClient

UTC = timezone.utc


def _raw_message(mid, subject, sender, epoch_ms, labels):
    return {
        "id": mid,
        "threadId": f"t-{mid}",
        "labelIds": labels,
        "internalDate": str(epoch_ms),
        "snippet": "extrait",
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": "Mon, 15 Jun 2026 12:00:00 +0000"},
            ]
        },
    }


def test_build_query_default_excludes_trash_and_spam():
    cutoff = datetime(2026, 4, 15, tzinfo=UTC)
    spec = build_query([], cutoff)
    assert "in:anywhere" in spec.text
    assert "-in:trash" in spec.text
    assert "-in:spam" in spec.text
    assert f"before:{int(cutoff.timestamp())}" in spec.text


def test_build_query_scope_inbox():
    cutoff = datetime(2026, 4, 15, tzinfo=UTC)
    spec = build_query([SearchScope.INBOX], cutoff)
    assert "in:inbox" in spec.text


def test_parse_message_metadata():
    epoch_ms = int(datetime(2025, 1, 10, 8, 30, tzinfo=UTC).timestamp() * 1000)
    raw = _raw_message(
        "m1",
        "Facture janvier",
        "Boutique <facture@boutique.com>",
        epoch_ms,
        ["INBOX", "STARRED", "CATEGORY_UPDATES"],
    )
    message = parse_message_metadata(raw, "UTC")
    assert message.id == "m1"
    assert message.subject == "Facture janvier"
    assert message.sender_email == "facture@boutique.com"
    assert message.is_starred is True
    assert message.is_in_inbox is True
    assert message.is_in_trash is False
    assert message.date == datetime(2025, 1, 10, 8, 30, tzinfo=UTC)


def test_parse_message_missing_subject():
    raw = _raw_message("m2", "", "a@b.com", 0, [])
    message = parse_message_metadata(raw, "UTC")
    assert message.subject == "(sans objet)"


def _make_message(mid, labels, subject="Sujet", sender="a@b.com"):
    return EmailMessage(
        id=mid,
        thread_id=f"t-{mid}",
        subject=subject,
        sender=sender,
        sender_email=sender,
        date=datetime(2025, 1, 1, tzinfo=UTC),
        label_ids=tuple(labels),
    )


def test_fake_client_pagination_covers_all_messages():
    messages = [_make_message(f"m{i}", ["INBOX"]) for i in range(5)]
    client = FakeGmailClient(messages, page_size=2)
    ids = list(client.iter_message_ids("in:inbox"))
    assert ids == [f"m{i}" for i in range(5)]


def test_fake_client_excludes_trash():
    messages = [
        _make_message("keep", ["INBOX"]),
        _make_message("trash", ["TRASH"]),
    ]
    client = FakeGmailClient(messages)
    ids = list(client.iter_message_ids("in:anywhere -in:trash"))
    assert ids == ["keep"]


def test_fake_client_get_profile():
    client = FakeGmailClient([_make_message("m1", ["INBOX"])], account_email="x@y.z")
    assert client.get_profile()["emailAddress"] == "x@y.z"
