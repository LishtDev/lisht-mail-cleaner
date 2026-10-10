"""Modeles de donnees partages par toute l'application.

Ces structures sont volontairement independantes de l'API Gmail et de
l'interface graphique : elles servent de contrat entre les couches et
permettent de tester la logique sans compte reel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Category(str, Enum):
    """Categories attribuables a un message (exigence section 8)."""

    ADVERTISING = "publicite_promotion"
    NEWSLETTER = "newsletter"
    AUTOMATED = "notification_automatique"
    SOCIAL = "reseau_social"
    ADMINISTRATIVE = "message_administratif"
    INVOICE = "facture_recu_potentiel"
    PERSONAL = "message_personnel"
    PROFESSIONAL = "professionnel_universitaire"
    POTENTIALLY_IMPORTANT = "potentiellement_important"
    UNKNOWN = "indetermine"


class Recommendation(str, Enum):
    """Recommandation produite par l'IA (jamais une decision finale)."""

    DELETE_CANDIDATE = "candidat_suppression"
    REVIEW = "a_verifier"
    KEEP = "conserver"


class ProtectionStatus(str, Enum):
    """Etat de protection d'un message."""

    PROTECTED_STAR = "protege_etoile"
    PROTECTED_SENDER = "protege_contact"
    PROTECTED_UNCERTAIN = "protege_incertain"
    NOT_ANALYZED = "non_analyse"
    NOT_PROTECTED = "non_protege"


@dataclass(frozen=True)
class EmailMessage:
    """Metadonnees d'un message Gmail (sans le corps complet)."""

    id: str
    thread_id: str = ""
    subject: str = ""
    sender: str = ""
    sender_email: str = ""
    date: datetime | None = None
    label_ids: tuple[str, ...] = ()
    is_starred: bool = False
    is_in_inbox: bool = False
    is_in_trash: bool = False
    is_in_spam: bool = False
    snippet: str = ""


@dataclass(frozen=True)
class Classification:
    """Sortie structuree et validee du classifieur."""

    category: Category = Category.UNKNOWN
    justification: str = ""
    confidence: float = 0.0
    recommendation: Recommendation = Recommendation.REVIEW
    caution: bool = True
    source: str = "rules"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence doit etre comprise entre 0 et 1")


@dataclass
class Candidate:
    """Message candidat a la suppression, avec sa classification et protection."""

    message: EmailMessage
    classification: Classification | None = None
    protection: ProtectionStatus = ProtectionStatus.NOT_ANALYZED
    selected: bool = False
    exclusion_reason: str = ""

    @property
    def is_eligible(self) -> bool:
        """Un message n'est eligible que s'il n'est pas protege et est classe."""
        return (
            self.classification is not None
            and self.protection == ProtectionStatus.NOT_PROTECTED
        )
