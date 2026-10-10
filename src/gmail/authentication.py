"""Authentification OAuth 2.0 aupres de Google (API Gmail).

Principes (section 5 et 14) :
- aucun mot de passe Gmail n'est jamais demande ni stocke ;
- les jetons sont conserves dans le trousseau du bureau (keyring) ;
- en dernier recours, un fichier local protege est utilise, avec avertissement.

Le perimetre de lecture `gmail.readonly` suffit pour analyser.
La suppression definitive exigera plus tard le perimetre complet
`https://mail.google.com/` (voir docs/GOOGLE_OAUTH.md).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.utils.logging_config import get_logger

READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
FULL_SCOPE = "https://mail.google.com/"

# Perimetres utilises par l'application.
SCOPES_READ = [READONLY_SCOPE]
SCOPES_TRASH = [MODIFY_SCOPE]
SCOPES_READ_WRITE = [FULL_SCOPE]  # requis pour la suppression definitive

# Niveaux d'acces proposes a l'utilisateur, du plus restreint au plus large.
ACCESS_LEVELS = {
    "lecture": SCOPES_READ,
    "corbeille": SCOPES_TRASH,
    "complet": SCOPES_READ_WRITE,
}
DEFAULT_ACCESS_LEVEL = "corbeille"


def scopes_for_level(level: str) -> list[str]:
    """Retourne la liste de perimetres OAuth correspondant a un niveau d'acces."""
    return list(ACCESS_LEVELS.get(level, SCOPES_TRASH))

KEYRING_SERVICE = "lisht-mail-cleaner"

logger = get_logger("gmail.auth")


class AuthenticationError(RuntimeError):
    """Erreur d'authentification lisible par l'utilisateur."""


@dataclass
class TokenStorage:
    """Stockage des jetons OAuth dans le trousseau, avec repli fichier."""

    fallback_dir: Path

    def _fallback_file(self, account: str) -> Path:
        safe = account.replace("/", "_").replace("\\", "_") or "default"
        return self.fallback_dir / f"token_{safe}.json"

    def save(self, account: str, token: dict) -> str:
        """Enregistre un jeton. Retourne 'keyring' ou 'fichier'."""
        try:
            import keyring

            keyring.set_password(KEYRING_SERVICE, account, json.dumps(token))
            return "keyring"
        except Exception as exc:  # pragma: no cover - depend du bureau
            logger.warning("Trousseau indisponible (%s), repli sur fichier protege", exc)
            self.fallback_dir.mkdir(parents=True, exist_ok=True)
            path = self._fallback_file(account)
            path.write_text(json.dumps(token), encoding="utf-8")
            try:
                path.chmod(0o600)
            except OSError:
                pass
            return "fichier"

    def load(self, account: str) -> dict | None:
        try:
            import keyring

            raw = keyring.get_password(KEYRING_SERVICE, account)
            if raw:
                return json.loads(raw)
        except Exception:  # pragma: no cover
            pass
        path = self._fallback_file(account)
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def delete(self, account: str) -> None:
        try:
            import keyring

            keyring.delete_password(KEYRING_SERVICE, account)
        except Exception:  # pragma: no cover
            pass
        path = self._fallback_file(account)
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    def list_accounts(self) -> list[str]:
        """Liste les comptes connus (repli fichier uniquement)."""
        if not self.fallback_dir.is_dir():
            return []
        accounts = []
        for path in self.fallback_dir.glob("token_*.json"):
            accounts.append(path.stem.removeprefix("token_"))
        return accounts


class GmailAuthenticator:
    """Gere le flux OAuth2 desktop et le cycle de vie des jetons."""

    def __init__(
        self,
        credentials_path: Path,
        token_storage: TokenStorage,
        scopes: list[str] | None = None,
    ) -> None:
        self.credentials_path = Path(credentials_path)
        self.token_storage = token_storage
        self.scopes = scopes or SCOPES_READ

    def has_client_config(self) -> bool:
        """Indique si le fichier credentials.json est present."""
        return self.credentials_path.is_file()

    def _load_client_config(self) -> dict:
        if not self.has_client_config():
            raise AuthenticationError(
                "Fichier credentials.json introuvable. "
                "Configurez un client OAuth de type « Application de bureau » "
                "(voir docs/GOOGLE_OAUTH.md)."
            )
        try:
            return json.loads(self.credentials_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthenticationError(
                f"Fichier credentials.json illisible ou invalide : {exc}"
            ) from exc

    def _build_credentials(self, token: dict):
        from google.oauth2.credentials import Credentials

        return Credentials.from_authorized_user_info(token, self.scopes)

    def load_saved_credentials(self, account: str):
        """Charge un jeton existant ; retourne None s'il est absent."""
        token = self.token_storage.load(account)
        if not token:
            return None
        try:
            return self._build_credentials(token)
        except Exception as exc:
            logger.warning("Jeton stocke invalide : %s", exc)
            return None

    def authenticate(self, account: str = "default"):
        """Execute le flux OAuth interactif et stocke le jeton.

        Ouvre le navigateur par defaut pour le consentement Google.
        """
        from google_auth_oauthlib.flow import InstalledAppFlow

        config = self._load_client_config()
        try:
            flow = InstalledAppFlow.from_client_config(config, self.scopes)
            credentials = flow.run_local_server(port=0)
        except Exception as exc:
            raise AuthenticationError(
                f"Echec du flux OAuth : {exc}. Verifiez que l'API Gmail est activee "
                "et que le consentement a ete accorde."
            ) from exc

        self.token_storage.save(account, json.loads(credentials.to_json()))
        logger.info("Authentification reussie (stockage du jeton effectue)")
        return credentials

    def get_credentials(self, account: str = "default"):
        """Retourne des identifiants valides, en rafraichissant si necessaire."""
        credentials = self.load_saved_credentials(account)
        if credentials is None:
            return None
        if credentials.expired and credentials.refresh_token:
            from google.auth.transport.requests import Request

            try:
                credentials.refresh(Request())
                self.token_storage.save(account, json.loads(credentials.to_json()))
            except Exception as exc:
                logger.warning("Rafraichissement du jeton impossible : %s", exc)
                return None
        return credentials

    def disconnect(self, account: str = "default") -> None:
        """Supprime les jetons locaux (ne revoque pas cote Google)."""
        self.token_storage.delete(account)
        from src.utils.validation import mask_email

        logger.info("Jetons locaux supprimes pour %s", mask_email(account))

    @staticmethod
    def revoke(credentials) -> bool:
        """Revoque l'acces cote Google. Retourne True si la revocation reussit."""
        try:
            import requests

            response = requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": credentials.token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            return response.status_code == 200
        except Exception as exc:  # pragma: no cover - reseau
            logger.warning("Revocation impossible : %s", exc)
            return False
