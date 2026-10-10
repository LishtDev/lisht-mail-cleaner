"""Tests du service de connexion, sans appel reseau reel."""

from __future__ import annotations

import pytest

from src.gmail.authentication import AuthenticationError
from src.gmail.fake_client import FakeGmailClient
from src.gmail.gmail_client import GmailClient
from src.services.connection_service import ConnectionService


class _FakeAuthenticator:
    """Faux authenticator : retourne un jeton factice non interactif."""

    def __init__(self, has_token: bool = True) -> None:
        self.has_token = has_token
        self.revoked = False
        self.disconnected = False

    def get_credentials(self, account="default"):
        return object() if self.has_token else None

    def authenticate(self, account="default"):
        return object()

    def revoke(self, credentials):
        self.revoked = True
        return True

    def disconnect(self, account="default"):
        self.disconnected = True


@pytest.fixture()
def fake_client():
    return FakeGmailClient([], account_email="me@example.com")


def test_connect_with_existing_token(monkeypatch, fake_client):
    monkeypatch.setattr(
        GmailClient, "from_credentials", classmethod(lambda cls, *a, **k: fake_client)
    )
    service = ConnectionService(_FakeAuthenticator(has_token=True), "UTC")
    profile = service.connect()
    assert profile["emailAddress"] == "me@example.com"
    assert service.is_connected is True
    assert service.client() is fake_client


def test_client_before_connect_raises():
    service = ConnectionService(_FakeAuthenticator(has_token=True), "UTC")
    with pytest.raises(AuthenticationError):
        service.client()


def test_connect_without_token_non_interactive(monkeypatch):
    service = ConnectionService(_FakeAuthenticator(has_token=False), "UTC")
    with pytest.raises(AuthenticationError):
        service.connect(interactive=False)


def test_disconnect(monkeypatch, fake_client):
    monkeypatch.setattr(
        GmailClient, "from_credentials", classmethod(lambda cls, *a, **k: fake_client)
    )
    auth = _FakeAuthenticator(has_token=True)
    service = ConnectionService(auth, "UTC")
    service.connect()
    service.disconnect(revoke=True)
    assert service.is_connected is False
    assert auth.revoked is True
    assert auth.disconnected is True
