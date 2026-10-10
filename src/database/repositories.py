"""Depots (repositories) d'acces aux donnees locales."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from src.database.database import Database
from src.utils.validation import is_valid_email, normalize_email


@dataclass(frozen=True)
class ProtectedContact:
    """Contact dont les messages sont exclus des candidats a la suppression."""

    email: str
    label: str = ""
    id: int | None = None
    created_at: str = ""


@dataclass
class OperationRecord:
    """Trace d'une operation (scan ou nettoyage) pour l'historique."""

    kind: str
    account: str = ""
    age_months: int = 2
    analyzed: int = 0
    excluded: int = 0
    protected: int = 0
    candidates: int = 0
    selected: int = 0
    deleted: int = 0
    failed: int = 0
    dry_run: bool = True
    status: str = "en_cours"
    details: str = ""
    id: int | None = None
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    finished_at: str | None = None

    def to_details_json(self) -> str:
        """Serialise des details libres en JSON (sans contenu d'e-mail)."""
        if not self.details:
            return ""
        try:
            return json.dumps({"message": self.details}, ensure_ascii=False)
        except (TypeError, ValueError):
            return ""


class SettingsRepository:
    """Stockage cle/valeur des preferences locales."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, key: str, default: str | None = None) -> str | None:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        with self.db.connect() as connection:
            connection.execute(
                "INSERT INTO app_settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_bool(self, key: str, default: bool) -> bool:
        raw = self.get(key)
        if raw is None:
            return default
        return raw.lower() in {"1", "true", "yes", "oui", "vrai"}

    def get_int(self, key: str, default: int) -> int:
        raw = self.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            return default


class ProtectedContactRepository:
    """Gestion de la liste locale des contacts proteges."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def list_all(self) -> list[ProtectedContact]:
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT id, email, label, created_at FROM protected_contacts "
                "ORDER BY email COLLATE NOCASE"
            ).fetchall()
        return [
            ProtectedContact(
                id=row["id"],
                email=row["email"],
                label=row["label"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def emails(self) -> set[str]:
        """Retourne l'ensemble normalise des adresses protegees."""
        return {normalize_email(c.email) for c in self.list_all()}

    def add(self, email: str, label: str = "") -> ProtectedContact:
        normalized = normalize_email(email)
        if not is_valid_email(normalized):
            raise ValueError(f"Adresse e-mail invalide : {email!r}")
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.db.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO protected_contacts(email, label, created_at) "
                "VALUES(?, ?, ?) "
                "ON CONFLICT(email) DO UPDATE SET label = excluded.label",
                (normalized, label.strip(), created),
            )
            new_id = cursor.lastrowid
        return ProtectedContact(email=normalized, label=label.strip(), id=new_id)

    def update(self, contact_id: int, email: str, label: str = "") -> None:
        normalized = normalize_email(email)
        if not is_valid_email(normalized):
            raise ValueError(f"Adresse e-mail invalide : {email!r}")
        with self.db.connect() as connection:
            connection.execute(
                "UPDATE protected_contacts SET email = ?, label = ? WHERE id = ?",
                (normalized, label.strip(), contact_id),
            )

    def delete(self, contact_id: int) -> None:
        with self.db.connect() as connection:
            connection.execute(
                "DELETE FROM protected_contacts WHERE id = ?", (contact_id,)
            )

    def import_many(self, addresses: list[str]) -> int:
        """Importe une liste d'adresses ; retourne le nombre d'ajouts valides."""
        count = 0
        for address in addresses:
            if is_valid_email(address):
                self.add(address)
                count += 1
        return count


class OperationRepository:
    """Historique des scans et des operations de nettoyage."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, record: OperationRecord) -> int:
        with self.db.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO operations(started_at, kind, account, age_months, dry_run, status) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                (
                    record.started_at,
                    record.kind,
                    record.account,
                    record.age_months,
                    int(record.dry_run),
                    record.status,
                ),
            )
            return int(cursor.lastrowid)

    def finish(self, operation_id: int, record: OperationRecord) -> None:
        record.finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.db.connect() as connection:
            connection.execute(
                "UPDATE operations SET finished_at=?, analyzed=?, excluded=?, protected=?, "
                "candidates=?, selected=?, deleted=?, failed=?, status=?, details=? "
                "WHERE id=?",
                (
                    record.finished_at,
                    record.analyzed,
                    record.excluded,
                    record.protected,
                    record.candidates,
                    record.selected,
                    record.deleted,
                    record.failed,
                    record.status,
                    record.to_details_json(),
                    operation_id,
                ),
            )

    def list_recent(self, limit: int = 50) -> list[dict]:
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM operations ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def to_export_dict(self, record: OperationRecord) -> dict:
        """Representation neutre pour export JSON/CSV."""
        data = asdict(record)
        data.pop("details", None)
        return data
