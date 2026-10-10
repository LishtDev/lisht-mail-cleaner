"""Acces a la base SQLite locale.

La base stocke uniquement des donnees locales : parametres, contacts
proteges et historique des operations. Elle ne contient jamais le corps
des e-mails, ni les jetons OAuth (stockes dans le trousseau du bureau).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS protected_contacts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL UNIQUE,
    label      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at     TEXT NOT NULL,
    finished_at    TEXT,
    kind           TEXT NOT NULL,
    account        TEXT NOT NULL DEFAULT '',
    age_months     INTEGER NOT NULL DEFAULT 2,
    analyzed       INTEGER NOT NULL DEFAULT 0,
    excluded       INTEGER NOT NULL DEFAULT 0,
    protected      INTEGER NOT NULL DEFAULT 0,
    candidates     INTEGER NOT NULL DEFAULT 0,
    selected       INTEGER NOT NULL DEFAULT 0,
    deleted        INTEGER NOT NULL DEFAULT 0,
    failed         INTEGER NOT NULL DEFAULT 0,
    dry_run        INTEGER NOT NULL DEFAULT 1,
    status         TEXT NOT NULL DEFAULT 'en_cours',
    details        TEXT NOT NULL DEFAULT ''
);
"""


class Database:
    """Encapsule une connexion SQLite avec initialisation du schema."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Fournit une connexion transactionnelle, fermee a la sortie."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Cree les tables si elles n'existent pas."""
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def secure_permissions(self) -> None:
        """Restreint les permissions du fichier de base au proprietaire."""
        if self.path.exists():
            try:
                self.path.chmod(0o600)
            except OSError:
                pass
