"""Construction des requetes Gmail et analyse des metadonnees.

Ce module ne parle pas directement a l'API : il transforme les reponses
brutes en objets `EmailMessage` et construit les requetes de recherche.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.core.models import EmailMessage
from src.utils.dates import get_zoneinfo
from src.utils.validation import extract_email

# Libelles Gmail utiles.
LABEL_INBOX = "INBOX"
LABEL_SENT = "SENT"
LABEL_TRASH = "TRASH"
LABEL_SPAM = "SPAM"
LABEL_STARRED = "STARRED"


class SearchScope(str, Enum):
    """Perimetres de recherche (section 7)."""

    ALL_MAIL = "all_mail"
    INBOX = "inbox"
    SENT = "sent"
    ARCHIVED = "archived"
    PROMOTIONS = "promotions"
    SOCIAL = "social"
    FORUMS = "forums"
    UPDATES = "updates"


# Operateurs Gmail associes a chaque perimetre.
# On exclut systematiquement la corbeille et le spam par defaut.
_SCOPE_QUERY = {
    SearchScope.ALL_MAIL: "in:anywhere -in:trash -in:spam",
    SearchScope.INBOX: "in:inbox",
    SearchScope.SENT: "in:sent",
    SearchScope.ARCHIVED: "-in:inbox -in:sent -in:trash -in:spam",
    SearchScope.PROMOTIONS: "category:promotions",
    SearchScope.SOCIAL: "category:social",
    SearchScope.FORUMS: "category:forums",
    SearchScope.UPDATES: "category:updates",
}


@dataclass(frozen=True)
class QuerySpec:
    """Requete Gmail complete avec sa tracabilite."""

    text: str
    cutoff: datetime
    scopes: tuple[SearchScope, ...]


def build_query(
    scopes: list[SearchScope] | tuple[SearchScope, ...],
    cutoff: datetime,
) -> QuerySpec:
    """Construit la requete Gmail pour les perimetres et la date limite donnes.

    On ajoute `before:` pour reduire cote serveur, mais la decision finale
    d'anciennete reste prise localement avec une comparaison de dates stricte.
    """
    if not scopes:
        scopes = (SearchScope.ALL_MAIL,)

    parts = [f"({_SCOPE_QUERY.get(scope, 'in:anywhere')})" for scope in scopes]
    # before: accepte l'epoque en secondes.
    parts.append(f"before:{int(cutoff.timestamp())}")
    return QuerySpec(text=" ".join(parts), cutoff=cutoff, scopes=tuple(scopes))


def _header(headers: list[dict], name: str) -> str:
    """Recupere la valeur d'un en-tete (insensible a la casse)."""
    lowered = name.lower()
    for header in headers or []:
        if header.get("name", "").lower() == lowered:
            return header.get("value", "")
    return ""


def parse_message_metadata(raw: dict, tz_name: str = "UTC") -> EmailMessage:
    """Transforme une reponse `messages.get` (format metadata) en EmailMessage."""
    from src.utils.dates import parse_gmail_date  # import local pour eviter un cycle

    payload = raw.get("payload", {}) or {}
    headers = payload.get("headers", []) or []
    label_ids = tuple(raw.get("labelIds", []) or [])

    internal_date = raw.get("internalDate")
    message_date: datetime | None = None
    if internal_date:
        try:
            message_date = datetime.fromtimestamp(int(internal_date) / 1000, tz=get_zoneinfo(tz_name))
        except (TypeError, ValueError, OSError):
            message_date = None
    if message_date is None:
        message_date = parse_gmail_date(_header(headers, "Date"), tz_name)

    sender = _header(headers, "From")
    return EmailMessage(
        id=str(raw.get("id", "")),
        thread_id=str(raw.get("threadId", "")),
        subject=_header(headers, "Subject") or "(sans objet)",
        sender=sender,
        sender_email=extract_email(sender),
        date=message_date,
        label_ids=label_ids,
        is_starred=LABEL_STARRED in label_ids,
        is_in_inbox=LABEL_INBOX in label_ids,
        is_in_trash=LABEL_TRASH in label_ids,
        is_in_spam=LABEL_SPAM in label_ids,
        snippet=raw.get("snippet", "") or "",
    )
