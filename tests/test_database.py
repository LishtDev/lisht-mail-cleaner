"""Tests de la base SQLite et des depots locaux."""

from __future__ import annotations

import pytest

from src.database.database import Database
from src.database.repositories import (
    OperationRepository,
    OperationRecord,
    ProtectedContactRepository,
    SettingsRepository,
)


@pytest.fixture()
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    database.initialize()
    return database


def test_settings_roundtrip(db):
    repo = SettingsRepository(db)
    assert repo.get("absent", "defaut") == "defaut"
    repo.set("cle", "valeur")
    assert repo.get("cle") == "valeur"
    repo.set("cle", "nouvelle")
    assert repo.get("cle") == "nouvelle"


def test_settings_bool_and_int(db):
    repo = SettingsRepository(db)
    repo.set("flag", "true")
    repo.set("nombre", "42")
    assert repo.get_bool("flag", False) is True
    assert repo.get_int("nombre", 0) == 42


def test_protected_contacts_crud(db):
    repo = ProtectedContactRepository(db)
    contact = repo.add("Alice@Example.com", "Famille")
    assert contact.email == "alice@example.com"

    assert repo.emails() == {"alice@example.com"}

    repo.update(contact.id, "alice@example.com", "Personnel")
    assert repo.list_all()[0].label == "Personnel"

    repo.delete(contact.id)
    assert repo.list_all() == []


def test_protected_contacts_reject_invalid(db):
    repo = ProtectedContactRepository(db)
    with pytest.raises(ValueError):
        repo.add("pas-une-adresse")


def test_protected_contacts_import(db):
    repo = ProtectedContactRepository(db)
    count = repo.import_many(["a@b.com", "invalide", "c@d.org"])
    assert count == 2
    assert repo.emails() == {"a@b.com", "c@d.org"}


def test_operation_history(db):
    repo = OperationRepository(db)
    record = OperationRecord(kind="scan", account="user@example.com", analyzed=10)
    op_id = repo.create(record)
    record.analyzed = 12
    record.status = "termine"
    repo.finish(op_id, record)

    recent = repo.list_recent()
    assert len(recent) == 1
    assert recent[0]["analyzed"] == 12
    assert recent[0]["status"] == "termine"
