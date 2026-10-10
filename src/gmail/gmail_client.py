"""Client Gmail reel s'appuyant sur l'API officielle Google.

Gere explicitement la pagination : l'analyse ne s'arrete jamais
silencieusement aux premiers resultats (section 7).

Les methodes de modification (corbeille / suppression definitive) sont
ajoutees et verrouillees a la phase 6. Ce module expose ici la lecture.
"""

from __future__ import annotations

from typing import Callable, Iterator

from src.core.models import EmailMessage
from src.gmail.email_repository import parse_message_metadata
from src.utils.logging_config import get_logger

logger = get_logger("gmail.client")

# En-tetes recuperes pour chaque message (metadonnees seulement).
METADATA_HEADERS = ["From", "To", "Subject", "Date", "Reply-To"]
_PAGE_SIZE = 500


class GmailApiError(RuntimeError):
    """Erreur lisible remontant de l'API Gmail."""


class GmailClient:
    """Implementation concrete du contrat `GmailClientProtocol`."""

    def __init__(self, service, tz_name: str = "UTC") -> None:
        self.service = service
        self.tz_name = tz_name

    @classmethod
    def from_credentials(
        cls, credentials, tz_name: str = "UTC", account: str = "default"
    ) -> "GmailClient":
        """Construit un client depuis des identifiants OAuth valides."""
        from googleapiclient.discovery import build

        try:
            service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        except Exception as exc:
            raise GmailApiError(
                f"Impossible de contacter l'API Gmail : {exc}"
            ) from exc
        return cls(service, tz_name)

    def get_profile(self) -> dict:
        """Retourne le profil du compte (emailAddress, totaux de messages)."""
        try:
            profile = self.service.users().getProfile(userId="me").execute()
        except Exception as exc:
            raise GmailApiError(_friendly_error(exc)) from exc
        return profile

    def account_email(self) -> str:
        return self.get_profile().get("emailAddress", "")

    def iter_message_ids(self, query: str) -> Iterator[str]:
        """Genere tous les identifiants de messages, page par page."""
        page_token = None
        page_number = 0
        while True:
            try:
                response = (
                    self.service.users()
                    .messages()
                    .list(
                        userId="me",
                        q=query,
                        pageToken=page_token,
                        maxResults=_PAGE_SIZE,
                    )
                    .execute()
                )
            except Exception as exc:
                raise GmailApiError(_friendly_error(exc)) from exc

            page_number += 1
            for message in response.get("messages", []):
                yield message["id"]

            page_token = response.get("nextPageToken")
            if not page_token:
                break
            logger.debug("Pagination Gmail : page %s traitee", page_number)
        logger.info("Pagination Gmail terminee : %s page(s)", page_number)

    def get_message_metadata(self, message_id: str) -> EmailMessage:
        """Recupere les metadonnees d'un message (sans le corps complet)."""
        try:
            raw = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=METADATA_HEADERS,
                )
                .execute()
            )
        except Exception as exc:
            raise GmailApiError(_friendly_error(exc)) from exc
        return parse_message_metadata(raw, self.tz_name)

    def get_message_body(self, message_id: str) -> str:
        """Recupere le corps texte d'un message (uniquement si necessaire).

        A n'utiliser que pour un apercu controle demande par l'utilisateur.
        """
        try:
            raw = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except Exception as exc:
            raise GmailApiError(_friendly_error(exc)) from exc
        return _extract_text_body(raw.get("payload", {}))

    # --- Operations de modification (phase 6) ---
    # Ces methodes ne doivent etre appelees que par CleanupService, apres
    # confirmation humaine explicite.

    def trash(self, message_id: str) -> None:
        """Deplace un message vers la corbeille (reversible)."""
        try:
            self.service.users().messages().trash(userId="me", id=message_id).execute()
        except Exception as exc:
            raise GmailApiError(_friendly_error(exc)) from exc

    def untrash(self, message_id: str) -> None:
        """Retire un message de la corbeille (restauration)."""
        try:
            self.service.users().messages().untrash(userId="me", id=message_id).execute()
        except Exception as exc:
            raise GmailApiError(_friendly_error(exc)) from exc

    def trash_many(self, message_ids: list[str]) -> None:
        """Deplace plusieurs messages vers la corbeille par lots (batchModify)."""
        for batch in _chunks(message_ids, 1000):
            body = {"ids": batch, "addLabelIds": ["TRASH"], "removeLabelIds": ["INBOX"]}
            try:
                self.service.users().messages().batchModify(userId="me", body=body).execute()
            except Exception as exc:
                raise GmailApiError(_friendly_error(exc)) from exc

    def delete(self, message_id: str) -> None:
        """Suppression DEFINITIVE et irreversible d'un message."""
        try:
            self.service.users().messages().delete(userId="me", id=message_id).execute()
        except Exception as exc:
            raise GmailApiError(_friendly_error(exc)) from exc

    def batch_delete(self, message_ids: list[str]) -> None:
        """Suppression DEFINITIVE par lots (batchDelete)."""
        for batch in _chunks(message_ids, 1000):
            try:
                self.service.users().messages().batchDelete(
                    userId="me", body={"ids": batch}
                ).execute()
            except Exception as exc:
                raise GmailApiError(_friendly_error(exc)) from exc


def _chunks(items: list[str], size: int) -> list[list[str]]:
    """Decoupe une liste en sous-listes de taille maximale `size`."""
    return [items[i : i + size] for i in range(0, len(items), size)]



def _extract_text_body(payload: dict) -> str:
    """Extrait le texte brut d'une charge utile Gmail (partie texte/plain)."""
    import base64

    def decode(data: str) -> str:
        try:
            return base64.urlsafe_b64decode(data.encode("ascii")).decode(
                "utf-8", errors="replace"
            )
        except Exception:
            return ""

    mime = payload.get("mimeType", "")
    body = payload.get("body", {}) or {}
    if mime == "text/plain" and body.get("data"):
        return decode(body["data"])
    for part in payload.get("parts", []) or []:
        text = _extract_text_body(part)
        if text:
            return text
    return ""


def _friendly_error(exc: Exception) -> str:
    """Traduit une erreur technique en message comprehensible (section 16)."""
    text = str(exc)
    lowered = text.lower()
    if "invalid_grant" in lowered or "revoked" in lowered:
        return "Jeton OAuth expire ou revoque. Reconnectez votre compte Gmail."
    if "insufficient" in lowered or "permission" in lowered:
        return "Permissions insuffisantes pour cette operation."
    if "quota" in lowered or "rate limit" in lowered:
        return "Quota d'API Gmail depasse. Reessayez plus tard."
    if "access not configured" in lowered or "has not been used" in lowered:
        return "L'API Gmail n'est pas activee sur votre projet Google Cloud."
    if "network" in lowered or "timed out" in lowered or "unreachable" in lowered:
        return "Connexion reseau indisponible."
    if "404" in text:
        return "Message introuvable (peut-etre deja supprime)."
    return f"Erreur de l'API Gmail : {text}"
