"""Generation et export des rapports (section 15).

Les rapports contiennent des chiffres et des metadonnees techniques
(identifiant Gmail, date, categorie...). Ils ne conservent pas le corps
des messages. Le compte est masque dans les exports.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from src.core.models import Candidate
from src.services.cleanup_service import CleanupResult
from src.services.scan_service import ScanResult
from src.ui.labels import category_label, protection_label, recommendation_label
from src.utils.dates import format_for_display
from src.utils.validation import mask_email

SPACE_NOTE = (
    "Le nombre de messages supprimes ne correspond pas necessairement a un "
    "volume d'espace libere immediatement mesurable."
)

CSV_COLUMNS = [
    "id_message",
    "date",
    "expediteur",
    "objet",
    "categorie",
    "confiance",
    "protection",
    "recommandation",
    "selectionne",
    "action_recommandee",
]


def build_report(
    scan: ScanResult | None,
    account: str = "",
    age_months: int = 2,
    cutoff: datetime | None = None,
    selected_count: int = 0,
    cleanup: CleanupResult | None = None,
    tz_name: str = "UTC",
    include_subject: bool = True,
) -> dict:
    """Construit un rapport serialisable a partir d'un scan et d'un nettoyage."""
    scanned = scan or ScanResult()
    report = {
        "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "compte": mask_email(account),
        "seuil_mois": age_months,
        "date_limite": format_for_display(cutoff, tz_name) if cutoff else "-",
        "messages_recuperes": scanned.fetched,
        "messages_exclus": scanned.excluded,
        "messages_analyses": scanned.analyzed,
        "messages_proteges": scanned.protected,
        "candidats": scanned.candidate_count,
        "messages_selectionnes": selected_count,
        "suppressions_reussies": cleanup.deleted if cleanup else 0,
        "messages_en_corbeille": cleanup.trashed if cleanup else 0,
        "echecs": cleanup.failed if cleanup else 0,
        "mode_simulation": cleanup.dry_run if cleanup else True,
        "note_espace_disque": SPACE_NOTE,
        "messages": [],
    }
    for candidate in scanned.candidates:
        report["messages"].append(
            _message_row(candidate, tz_name, include_subject=include_subject)
        )
    return report


def _message_row(candidate: Candidate, tz_name: str, include_subject: bool) -> dict:
    message = candidate.message
    classification = candidate.classification
    return {
        "id_message": message.id,
        "date": format_for_display(message.date, tz_name),
        "expediteur": mask_email(message.sender_email) if message.sender_email else "(inconnu)",
        "objet": (message.subject or "")[:120] if include_subject else "",
        "categorie": category_label(classification.category if classification else None),
        "confiance": f"{classification.confidence:.2f}" if classification else "-",
        "protection": protection_label(candidate.protection),
        "recommandation": recommendation_label(
            classification.recommendation if classification else None
        ),
        "selectionne": "oui" if candidate.selected else "non",
        "action_recommandee": (
            classification.recommendation.value if classification else "-"
        ),
    }


def write_json(report: dict, path: Path | str) -> Path:
    """Ecrit un rapport au format JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def write_csv(report: dict, path: Path | str) -> Path:
    """Ecrit un rapport au format CSV (une ligne par message)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in report.get("messages", []):
            writer.writerow({key: row.get(key, "") for key in CSV_COLUMNS})
    return path
