"""Service de connexion Gmail : relie l'authentification OAuth au client API.

Aucune suppression n'est effectuee ici. Ce service fournit un client pret
a lire les messages, ou explique clairement pourquoi la connexion echoue.
"""

from __future__ import annotations

from src.gmail.authentication import (
    DEFAULT_ACCESS_LEVEL,
    SCOPES_TRASH,
    AuthenticationError,
    GmailAuthenticator,
    TokenStorage,
    scopes_for_level,
)
from src.gmail.gmail_client import GmailApiError, GmailClient
from src.utils.logging_config import get_logger

logger = get_logger("services.connection")

DEFAULT_ACCOUNT = "default"


class ConnectionService:
    """Gere l'etat de la connexion Gmail pour l'application."""

    def __init__(
        self,
        authenticator: GmailAuthenticator,
        tz_name: str = "UTC",
        access_level: str = DEFAULT_ACCESS_LEVEL,
    ) -> None:
        self.authenticator = authenticator
        self.tz_name = tz_name
        self.access_level = access_level
        self._account_email = ""
        self._client: GmailClient | None = None

    @classmethod
    def create(
        cls,
        credentials_path,
        fallback_dir,
        tz_name: str = "UTC",
        scopes=None,
        access_level: str = DEFAULT_ACCESS_LEVEL,
    ):
        """Fabrique standard a partir des chemins de configuration."""
        authenticator = GmailAuthenticator(
            credentials_path,
            TokenStorage(fallback_dir),
            scopes=scopes or scopes_for_level(access_level),
        )
        return cls(authenticator, tz_name, access_level=access_level)

    @property
    def account_email(self) -> str:
        return self._account_email

    @property
    def is_connected(self) -> bool:
        return bool(self._account_email)

    def _token_key(self) -> str:
        """Cle de stockage dependant du niveau d'acces.

        Changer de niveau force un nouveau consentement (le jeton precedent
        ne couvre pas necessairement les nouveaux droits).
        """
        return f"{DEFAULT_ACCOUNT}:{self.access_level}"

    def set_access_level(self, level: str) -> None:
        """Change le niveau d'acces et invalide la connexion en cours."""
        if level == self.access_level:
            return
        self.access_level = level
        self.authenticator.scopes = scopes_for_level(level)
        self._client = None
        self._account_email = ""
        logger.info("Niveau d'acces Gmail modifie : %s", level)

    def connect(self, interactive: bool = True):
        """Etablit la connexion. Passe par le navigateur si necessaire.

        Si un jeton valide existe deja, aucun navigateur n'est ouvert.
        """
        credentials = self.authenticator.get_credentials(self._token_key())
        if credentials is None:
            if not interactive:
                raise AuthenticationError("Compte non connecte.")
            credentials = self.authenticator.authenticate(self._token_key())

        client = GmailClient.from_credentials(credentials, self.tz_name)
        try:
            profile = client.get_profile()
        except GmailApiError as exc:
            raise AuthenticationError(str(exc)) from exc

        self._client = client
        self._account_email = profile.get("emailAddress", "")
        logger.info("Connecte au compte Gmail (acces : %s)", self.access_level)
        return profile

    def client(self) -> GmailClient:
        """Retourne le client connecte, ou leve une erreur claire."""
        if self._client is None:
            raise AuthenticationError("Compte non connecte. Cliquez sur « Connecter Gmail ».")
        return self._client

    def disconnect(self, revoke: bool = False) -> None:
        """Deconnecte l'application. Revoque l'acces si demande."""
        credentials = self.authenticator.get_credentials(self._token_key())
        if revoke and credentials is not None:
            self.authenticator.revoke(credentials)
        self.authenticator.disconnect(self._token_key())
        self._client = None
        self._account_email = ""
        logger.info("Deconnexion effectuee")
