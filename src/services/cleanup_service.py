"""Service de nettoyage controle (section 11, 12 et 9).

C'est LE SEUL endroit de l'application autorise a appeler une methode
destructive de Gmail. Toutes les garanties y sont centralisees :

- jamais d'action destructive en mode simulation ;
- confirmation humaine explicite exigee ;
- phrase EXACTE exigee pour la suppression definitive ;
- revérification des protections et de l'existence juste avant l'action ;
- limite du nombre de messages par operation ;
- arret en cas d'erreur, avec rapport des resultats partiels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable

from src.core.models import Candidate, ProtectionStatus
from src.services.protection_service import ProtectionService
from src.utils.dates import is_older_than_cutoff
from src.utils.logging_config import get_logger

logger = get_logger("services.cleanup")

# Phrase exacte a saisir pour autoriser une suppression definitive.
REQUIRED_DELETE_PHRASE = "SUPPRIMER DÉFINITIVEMENT"
BATCH_SIZE = 50


class CleanupMode(str, Enum):
    TRASH = "trash"
    DELETE = "delete"


class CleanupError(RuntimeError):
    """Erreur lisible empechant une operation de nettoyage."""


class LimitExceededError(CleanupError):
    """Le nombre de messages depasse la limite autorisee pour l'operation."""


@dataclass
class Confirmation:
    """Autorisation explicite donnee par l'utilisateur.

    `human_validated` ne doit etre mis a True que par une action directe de
    l'utilisateur (clic dans la fenetre de confirmation). Jamais par l'IA.
    """

    mode: CleanupMode
    confirmed_count: int
    account: str = ""
    cutoff: datetime | None = None
    phrase: str = ""
    human_validated: bool = False
    dry_run: bool = True

    def is_valid_for(self, actual_count: int) -> bool:
        """Verifie que la confirmation couvre exactement le nombre a traiter."""
        if not self.human_validated:
            return False
        if self.confirmed_count != actual_count:
            return False
        if self.mode == CleanupMode.DELETE:
            return self.phrase.strip() == REQUIRED_DELETE_PHRASE
        return True


@dataclass
class CleanupResult:
    """Resultat d'une operation de nettoyage (simulation ou reelle)."""

    mode: CleanupMode = CleanupMode.TRASH
    dry_run: bool = True
    deleted: int = 0
    trashed: int = 0
    skipped: int = 0
    failed: int = 0
    details: list[str] = field(default_factory=list)
    stopped_early: bool = False
    processed_ids: list[str] = field(default_factory=list)

    @property
    def processed(self) -> int:
        return self.deleted + self.trashed


class CleanupService:
    """Execute les operations de nettoyage de maniere sure et tracee."""

    def __init__(
        self,
        client,
        protection: ProtectionService,
        max_delete: int = 50,
        dry_run: bool = True,
        tz_name: str = "UTC",
        progress: Callable[[int, str], None] | None = None,
    ) -> None:
        self.client = client
        self.protection = protection
        self.max_delete = max(1, max_delete)
        self.dry_run = dry_run
        self.tz_name = tz_name
        self.progress = progress

    def _report(self, count: int, text: str) -> None:
        if self.progress is not None:
            try:
                self.progress(count, text)
            except Exception:  # pragma: no cover
                pass

    def revalidate(
        self, candidates: list[Candidate], cutoff: datetime | None
    ) -> tuple[list[Candidate], list[str]]:
        """Revérifie chaque message juste avant l'action.

        Retourne (messages encore admissibles, raisons d'exclusion).
        """
        eligible: list[Candidate] = []
        excluded: list[str] = []
        for candidate in candidates:
            message_id = candidate.message.id
            try:
                fresh = self.client.get_message_metadata(message_id)
            except Exception:
                excluded.append(f"{message_id} : message introuvable (deja supprime ?)")
                continue

            status = self.protection.evaluate(fresh, analyzed=True)
            if ProtectionService.is_protected(status):
                excluded.append(f"{message_id} : protege entre-temps ({status.value})")
                continue
            if cutoff is not None and not is_older_than_cutoff(fresh.date, cutoff):
                excluded.append(f"{message_id} : n'est plus anterieur a la date limite")
                continue
            candidate.message = fresh
            eligible.append(candidate)
        return eligible, excluded

    def execute(
        self,
        candidates: list[Candidate],
        mode: CleanupMode,
        confirmation: Confirmation,
        cutoff: datetime | None = None,
    ) -> CleanupResult:
        """Execute (ou simule) le nettoyage des candidats fournis."""
        result = CleanupResult(mode=mode, dry_run=self.dry_run or confirmation.dry_run)

        if not candidates:
            result.details.append("Aucun message selectionne.")
            return result

        # 1. Verification stricte de la confirmation.
        if not confirmation.is_valid_for(len(candidates)):
            raise CleanupError(
                "Confirmation invalide : l'operation destructive est refusee. "
                "Une confirmation humaine explicite est obligatoire."
            )
        if confirmation.mode != mode:
            raise CleanupError("La confirmation ne correspond pas au mode demande.")

        # 2. Limite par operation.
        if len(candidates) > self.max_delete:
            raise LimitExceededError(
                f"Le nombre de messages ({len(candidates)}) depasse la limite "
                f"configuree ({self.max_delete}). Reduisez la selection ou augmentez la limite."
            )

        # 3. Revérification des protections et de l'existence.
        eligible, excluded = self.revalidate(candidates, cutoff)
        for reason in excluded:
            result.details.append(f"Ecarte : {reason}")
        result.skipped = len(excluded)

        if self.dry_run or confirmation.dry_run:
            # Simulation : AUCUN appel de modification.
            result.details.append(
                f"SIMULATION : {len(eligible)} message(s) auraient ete traites "
                f"en mode {mode.value}."
            )
            return result

        # 4. Execution reelle.
        if mode == CleanupMode.TRASH:
            self._execute_trash(eligible, result)
        else:
            self._execute_delete(eligible, result)

        return result

    def _execute_trash(self, candidates: list[Candidate], result: CleanupResult) -> None:
        """Mise en corbeille (reversible), par lots."""
        ids = [c.message.id for c in candidates]
        for index, batch in enumerate(_chunks(ids, BATCH_SIZE), start=1):
            self._report(index, f"Mise en corbeille du lot {index}...")
            try:
                self.client.trash_many(batch)
                result.trashed += len(batch)
                result.processed_ids.extend(batch)
                result.details.append(f"Lot {index} : {len(batch)} message(s) en corbeille.")
            except Exception as exc:
                # Repli individuel pour ne pas perdre le lot entier.
                for message_id in batch:
                    try:
                        self.client.trash(message_id)
                        result.trashed += 1
                        result.processed_ids.append(message_id)
                    except Exception as inner:
                        result.failed += 1
                        result.details.append(f"Echec {message_id} : {inner}")
                result.details.append(f"Lot {index} partiel ({exc}).")

    def _execute_delete(self, candidates: list[Candidate], result: CleanupResult) -> None:
        """Suppression definitive, par lots maitrises."""
        ids = [c.message.id for c in candidates]
        for index, batch in enumerate(_chunks(ids, BATCH_SIZE), start=1):
            self._report(index, f"Suppression definitive du lot {index}...")
            try:
                self.client.batch_delete(batch)
                result.deleted += len(batch)
                result.processed_ids.extend(batch)
                result.details.append(
                    f"Lot {index} : {len(batch)} message(s) supprimes definitivement."
                )
            except Exception as exc:
                result.stopped_early = True
                result.details.append(
                    f"Arret apres erreur sur le lot {index} ({exc}). "
                    "Les messages deja supprimes ne peuvent pas etre restaures par l'application."
                )
                break


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]
