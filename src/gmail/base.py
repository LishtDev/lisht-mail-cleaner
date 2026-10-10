"""Interface abstraite d'un client Gmail.

Permet de remplacer le vrai client par un faux client de simulation dans
les tests et le mode maquette, sans modifier les services qui l'utilisent.
"""

from __future__ import annotations

from typing import Callable, Iterator, Protocol, runtime_checkable

from src.core.models import EmailMessage

ProgressCallback = Callable[[int, str], None]


@runtime_checkable
class GmailClientProtocol(Protocol):
    """Contrat minimal attendu par les services applicatifs."""

    def get_profile(self) -> dict:
        """Retourne le profil du compte connecte (emailAddress, totaux)."""
        ...

    def iter_message_ids(self, query: str) -> Iterator[str]:
        """Parcourt tous les identifiants de messages correspondant a `query`.

        Doit gerer la pagination de l'API Gmail et ne jamais s'arreter
        silencieusement aux premiers resultats.
        """
        ...

    def get_message_metadata(self, message_id: str) -> EmailMessage:
        """Retourne les metadonnees d'un message sans le corps complet."""
        ...
