"""Application des regles de protection (section 9).

En cas de doute, un message est PROTEGE : on ne supprime jamais par
supposition. Ces regles sont revérifiées juste avant toute suppression
reelle a la phase 6.
"""

from __future__ import annotations

from src.core.models import EmailMessage, ProtectionStatus
from src.utils.validation import normalize_email


class ProtectionService:
    """Determine si un message doit etre exclu des candidats a la suppression."""

    def __init__(
        self,
        protected_emails: set[str] | None = None,
        protect_starred: bool = True,
        protect_uncertain_sender: bool = True,
    ) -> None:
        self.protected_emails = {
            normalize_email(email) for email in (protected_emails or set())
        }
        self.protect_starred = protect_starred
        self.protect_uncertain_sender = protect_uncertain_sender

    def evaluate(
        self, message: EmailMessage, analyzed: bool = True
    ) -> ProtectionStatus:
        """Retourne le statut de protection d'un message."""
        if not analyzed:
            return ProtectionStatus.NOT_ANALYZED

        if self.protect_starred and message.is_starred:
            return ProtectionStatus.PROTECTED_STAR

        sender = normalize_email(message.sender_email or "")
        if not sender:
            if self.protect_uncertain_sender:
                return ProtectionStatus.PROTECTED_UNCERTAIN
        elif sender in self.protected_emails:
            return ProtectionStatus.PROTECTED_SENDER

        return ProtectionStatus.NOT_PROTECTED

    @staticmethod
    def is_protected(status: ProtectionStatus) -> bool:
        """Indique si un statut correspond a une protection (exclusion)."""
        return status in {
            ProtectionStatus.PROTECTED_STAR,
            ProtectionStatus.PROTECTED_SENDER,
            ProtectionStatus.PROTECTED_UNCERTAIN,
            ProtectionStatus.NOT_ANALYZED,
        }
