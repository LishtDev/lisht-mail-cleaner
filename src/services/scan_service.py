"""Service de scan : construit la liste des candidats a la suppression.

Ce service est STRICTEMENT en lecture seule : il ne modifie jamais Gmail.
Le cycle suit les etapes 5 a 10 de la section 11.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from src.core.models import Candidate, EmailMessage, ProtectionStatus
from src.gmail.email_repository import QuerySpec
from src.services.protection_service import ProtectionService
from src.utils.dates import is_older_than_cutoff
from src.utils.logging_config import get_logger

logger = get_logger("services.scan")

ProgressCallback = Callable[[int, str], None]


@dataclass
class ScanResult:
    """Resultat d'un scan (lecture seule)."""

    account: str = ""
    fetched: int = 0
    excluded: int = 0
    analyzed: int = 0
    protected: int = 0
    candidates: list[Candidate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    classifier_source: str = "rules"
    cancelled: bool = False

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)


class ScanService:
    """Orchestre la recuperation, le filtrage, la protection et la classification."""

    def __init__(
        self,
        client,
        classifier,
        protection: ProtectionService,
        tz_name: str = "UTC",
        progress: ProgressCallback | None = None,
        max_messages: int | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> None:
        self.client = client
        self.classifier = classifier
        self.protection = protection
        self.tz_name = tz_name
        self.progress = progress
        self.max_messages = max_messages
        self.cancel_check = cancel_check

    def _report(self, count: int, text: str) -> None:
        if self.progress is not None:
            try:
                self.progress(count, text)
            except Exception:  # pragma: no cover - le callback ne doit pas casser le scan
                pass

    def scan(self, query_spec: QuerySpec, account: str = "") -> ScanResult:
        """Execute le scan complet en lecture seule."""
        result = ScanResult(account=account)
        result.classifier_source = getattr(self.classifier, "source_name", "rules")

        cutoff = query_spec.cutoff
        self._report(0, "Recuperation des identifiants de messages...")

        try:
            message_ids = list(self.client.iter_message_ids(query_spec.text))
        except Exception as exc:
            result.errors.append(f"Erreur lors de la liste des messages : {exc}")
            return result

        total = len(message_ids)
        if self.max_messages is not None:
            message_ids = message_ids[: self.max_messages]
            total = len(message_ids)

        for index, message_id in enumerate(message_ids, start=1):
            if self.cancel_check is not None and self.cancel_check():
                result.errors.append("Analyse interrompue par l'utilisateur.")
                result.cancelled = True
                logger.info("Scan interrompu a la demande de l'utilisateur")
                break
            result.fetched += 1
            self._report(index, f"Analyse du message {index}/{total}...")
            try:
                message = self.client.get_message_metadata(message_id)
            except Exception as exc:
                result.errors.append(f"Message {message_id} ignore : {exc}")
                result.excluded += 1
                continue

            if not self._is_in_scope(message):
                result.excluded += 1
                continue

            if not is_older_than_cutoff(message.date, cutoff):
                result.excluded += 1
                continue

            result.analyzed += 1
            status = self.protection.evaluate(message, analyzed=True)
            if ProtectionService.is_protected(status):
                result.protected += 1
                result.candidates.append(
                    Candidate(
                        message=message,
                        classification=None,
                        protection=status,
                        selected=False,
                        exclusion_reason=_protection_label(status),
                    )
                )
                continue

            classification = self.classifier.classify(message)
            result.candidates.append(
                Candidate(
                    message=message,
                    classification=classification,
                    protection=ProtectionStatus.NOT_PROTECTED,
                    # Un message n'est jamais preselectionne automatiquement.
                    selected=False,
                )
            )

        self._report(total, "Scan termine.")
        logger.info(
            "Scan termine : %s analyses, %s proteges, %s candidats",
            result.analyzed,
            result.protected,
            result.candidate_count,
        )
        return result

    @staticmethod
    def _is_in_scope(message: EmailMessage) -> bool:
        """Exclut par prudence corbeille et spam, meme si la requete les omet."""
        return not (message.is_in_trash or message.is_in_spam)


def _protection_label(status: ProtectionStatus) -> str:
    labels = {
        ProtectionStatus.PROTECTED_STAR: "Message etoile",
        ProtectionStatus.PROTECTED_SENDER: "Expediteur dans les contacts proteges",
        ProtectionStatus.PROTECTED_UNCERTAIN: "Expediteur non verifiable (prudence)",
        ProtectionStatus.NOT_ANALYZED: "Message non analyse",
    }
    return labels.get(status, "")
