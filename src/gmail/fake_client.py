"""Faux client Gmail pour les tests et le mode maquette.

Attention : ce client ne contacte jamais Google. Il sert uniquement a
tester la logique et a alimenter l'interface sans compte reel. Il ne doit
jamais etre presente comme une connexion Gmail operationnelle.
"""

from __future__ import annotations

from typing import Iterator

from src.core.models import EmailMessage
from src.gmail.email_repository import build_query

# Libelles reconnus par le faux client pour filtrer les messages.
_LABEL_STRING_TO_LABEL = {
    "INBOX": "INBOX",
    "SENT": "SENT",
    "TRASH": "TRASH",
    "SPAM": "SPAM",
    "STARRED": "STARRED",
}


class FakeGmailClient:
    """Implementation en memoire du contrat GmailClientProtocol."""

    def __init__(
        self,
        messages: list[EmailMessage],
        account_email: str = "test@example.com",
        page_size: int = 2,
    ) -> None:
        self._messages = {message.id: message for message in messages}
        self._order = [message.id for message in messages]
        self.account_email = account_email
        self.page_size = page_size
        self.deleted: list[str] = []
        self.trashed: list[str] = []

    def get_profile(self) -> dict:
        return {
            "emailAddress": self.account_email,
            "messagesTotal": len(self._messages),
            "threadsTotal": len(self._messages),
        }

    def _matches(self, message: EmailMessage, query: str) -> bool:
        """Filtrage simplifie : labels, exclusion, mot-cle sujet/expediteur."""
        for token in query.split():
            if token.startswith("-in:"):
                label = _LABEL_STRING_TO_LABEL.get(token[4:].upper())
                if label and label in message.label_ids:
                    return False
            elif token.startswith("in:"):
                label = _LABEL_STRING_TO_LABEL.get(token[3:].upper())
                if label and label not in message.label_ids:
                    return False
        return True

    def iter_message_ids(self, query: str) -> Iterator[str]:
        """Genere les identifiants par pages simulees."""
        matching = [
            mid for mid in self._order if self._matches(self._messages[mid], query)
        ]
        for start in range(0, len(matching), self.page_size):
            for mid in matching[start : start + self.page_size]:
                yield mid

    def get_message_metadata(self, message_id: str) -> EmailMessage:
        return self._messages[message_id]

    def get_message_body(self, message_id: str) -> str:
        message = self._messages[message_id]
        return message.snippet or f"Corps simule du message {message_id}."

    def delete(self, message_id: str) -> None:
        """Suppression simulee (jamais un vrai effacement)."""
        self.deleted.append(message_id)
        self._messages.pop(message_id, None)

    def trash(self, message_id: str) -> None:
        """Mise en corbeille simulee."""
        self.trashed.append(message_id)

    def untrash(self, message_id: str) -> None:
        """Sortie de corbeille simulee."""
        if message_id in self.trashed:
            self.trashed.remove(message_id)

    def trash_many(self, message_ids: list[str]) -> None:
        for message_id in message_ids:
            self.trash(message_id)

    def batch_delete(self, message_ids: list[str]) -> None:
        for message_id in message_ids:
            self.delete(message_id)

    def count_query(self, query: str) -> int:
        """Compte les messages correspondant a une requete (utilitaire de test)."""
        return sum(1 for _ in self.iter_message_ids(query))
