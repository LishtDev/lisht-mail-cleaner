"""Tests de l'authentification : perimetres, configuration, stockage de jeton.

Aucun appel reseau ni au trousseau reel n'est effectue.
"""

from __future__ import annotations

import json

import pytest

from src.gmail.authentication import (
    FULL_SCOPE,
    MODIFY_SCOPE,
    READONLY_SCOPE,
    AuthenticationError,
    GmailAuthenticator,
    TokenStorage,
)


def test_scope_constants():
    assert READONLY_SCOPE == "https://www.googleapis.com/auth/gmail.readonly"
    assert MODIFY_SCOPE == "https://www.googleapis.com/auth/gmail.modify"
    assert FULL_SCOPE == "https://mail.google.com/"


def test_missing_credentials_file(tmp_path):
    auth = GmailAuthenticator(tmp_path / "absent.json", TokenStorage(tmp_path))
    assert auth.has_client_config() is False
    with pytest.raises(AuthenticationError):
        auth._load_client_config()


def test_invalid_credentials_file(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("pas du json", encoding="utf-8")
    auth = GmailAuthenticator(bad, TokenStorage(tmp_path))
    with pytest.raises(AuthenticationError):
        auth._load_client_config()


def test_token_storage_fallback_roundtrip(tmp_path):
    storage = TokenStorage(tmp_path)
    path = storage._fallback_file("user@example.com")
    path.write_text(json.dumps({"token": "abc"}), encoding="utf-8")

    loaded = storage.load("user@example.com")
    assert loaded == {"token": "abc"}

    storage.delete("user@example.com")
    assert storage.load("user@example.com") is None


def test_token_storage_list_accounts(tmp_path):
    storage = TokenStorage(tmp_path)
    (tmp_path / "token_a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "token_b.json").write_text("{}", encoding="utf-8")
    assert sorted(storage.list_accounts()) == ["a", "b"]
