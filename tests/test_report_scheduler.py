"""Tests des rapports et de la planification (phase 7)."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone

from src.core.models import (
    Candidate,
    Category,
    Classification,
    EmailMessage,
    ProtectionStatus,
    Recommendation,
)
from src.services.cleanup_service import CleanupMode, CleanupResult
from src.services.report_service import build_report, write_csv, write_json
from src.services.scan_service import ScanResult
from src.services.scheduler_service import (
    SchedulerService,
    compute_next_run,
)

UTC = timezone.utc
CUTOFF = datetime(2026, 4, 15, tzinfo=UTC)


def _candidate(mid, category=Category.ADVERTISING):
    message = EmailMessage(
        id=mid,
        subject="Objet " + mid,
        sender="Nom <user@example.com>",
        sender_email="user@example.com",
        date=datetime(2025, 1, 1, tzinfo=UTC),
        label_ids=("INBOX",),
        is_in_inbox=True,
    )
    return Candidate(
        message=message,
        classification=Classification(
            category=category,
            recommendation=Recommendation.DELETE_CANDIDATE,
            confidence=0.9,
        ),
        protection=ProtectionStatus.NOT_PROTECTED,
        selected=True,
    )


def test_build_report_includes_counts_and_space_note():
    scan = ScanResult(
        fetched=10,
        excluded=3,
        analyzed=7,
        protected=1,
        candidates=[_candidate("m1")],
    )
    cleanup = CleanupResult(
        mode=CleanupMode.TRASH, dry_run=False, trashed=1, processed_ids=["m1"]
    )
    report = build_report(
        scan,
        account="alice@example.com",
        age_months=2,
        cutoff=CUTOFF,
        selected_count=1,
        cleanup=cleanup,
    )
    assert report["compte"] == "a***e@example.com"
    assert report["messages_recuperes"] == 10
    assert report["messages_analyses"] == 7
    assert report["messages_proteges"] == 1
    assert report["messages_selectionnes"] == 1
    assert report["messages_en_corbeille"] == 1
    assert "espace" in report["note_espace_disque"].lower()
    assert report["messages"][0]["expediteur"] == "u**r@example.com"
    assert report["messages"][0]["categorie"] == "Publicite / promotion"


def test_write_json_and_csv_roundtrip(tmp_path):
    scan = ScanResult(fetched=1, analyzed=1, candidates=[_candidate("m1")])
    report = build_report(scan, account="a@b.com", cutoff=CUTOFF)

    json_path = write_json(report, tmp_path / "rapport.json")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["compte"] == "a*@b.com"

    csv_path = write_csv(report, tmp_path / "rapport.csv")
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["id_message"] == "m1"
    assert rows[0]["categorie"] == "Publicite / promotion"


def test_export_does_not_include_message_body(tmp_path):
    scan = ScanResult(fetched=1, analyzed=1, candidates=[_candidate("m1")])
    report = build_report(scan, cutoff=CUTOFF)
    serialized = json.dumps(report, ensure_ascii=False)
    assert "snippet" not in serialized
    assert "body" not in serialized.lower()


def test_compute_next_run_same_week():
    now = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)  # lundi
    nxt = compute_next_run(now, weekday=4, hour=9, minute=30, tz_name="UTC")
    assert nxt == datetime(2026, 6, 5, 9, 30, tzinfo=UTC)


def test_compute_next_run_wraps_to_next_week():
    now = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)  # vendredi 10h
    nxt = compute_next_run(now, weekday=4, hour=9, tz_name="UTC")  # vendredi 9h
    assert nxt == datetime(2026, 6, 12, 9, 0, tzinfo=UTC)


def test_compute_next_run_across_dst():
    # Europe/Paris : DST le 29 mars 2026. La prochaine execution a 9h locale.
    now = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
    nxt = compute_next_run(now, weekday=6, hour=9, tz_name="Europe/Paris")
    assert nxt.hour == 9
    assert nxt.utcoffset() == timedelta(hours=2)


def test_scheduler_configure_validates():
    service = SchedulerService(callback=lambda: None, tz_name="UTC")
    service.configure(weekday=2, hour=14, minute=15)
    assert (service.weekday, service.hour, service.minute) == (2, 14, 15)
    try:
        service.configure(weekday=9, hour=1)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("jour invalide accepte")


def test_scheduler_next_run_without_start():
    service = SchedulerService(callback=lambda: None, tz_name="UTC")
    service.configure(weekday=0, hour=6)
    now = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)  # mercredi
    nxt = service.next_run(now=now)
    assert nxt == datetime(2026, 6, 8, 6, 0, tzinfo=UTC)
