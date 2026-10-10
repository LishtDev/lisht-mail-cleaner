"""Libelles francais pour les valeurs des modeles (interface)."""

from __future__ import annotations

from src.core.models import Category, ProtectionStatus, Recommendation

CATEGORY_LABELS = {
    Category.ADVERTISING: "Publicite / promotion",
    Category.NEWSLETTER: "Newsletter",
    Category.AUTOMATED: "Notification automatique",
    Category.SOCIAL: "Reseau social",
    Category.ADMINISTRATIVE: "Administratif",
    Category.INVOICE: "Facture / recu",
    Category.PERSONAL: "Personnel",
    Category.PROFESSIONAL: "Professionnel / universitaire",
    Category.POTENTIALLY_IMPORTANT: "Potentiellement important",
    Category.UNKNOWN: "Indetermine",
}

RECOMMENDATION_LABELS = {
    Recommendation.DELETE_CANDIDATE: "Candidat a la suppression",
    Recommendation.REVIEW: "A verifier",
    Recommendation.KEEP: "Conserver",
}

PROTECTION_LABELS = {
    ProtectionStatus.PROTECTED_STAR: "Etoile (protege)",
    ProtectionStatus.PROTECTED_SENDER: "Contact protege",
    ProtectionStatus.PROTECTED_UNCERTAIN: "Expediteur incertain",
    ProtectionStatus.NOT_ANALYZED: "Non analyse",
    ProtectionStatus.NOT_PROTECTED: "Non protege",
}


def category_label(category: Category | None) -> str:
    return CATEGORY_LABELS.get(category, "Indetermine") if category else "Non classe"


def recommendation_label(recommendation) -> str:
    return RECOMMENDATION_LABELS.get(recommendation, "-") if recommendation else "-"


def protection_label(status: ProtectionStatus) -> str:
    return PROTECTION_LABELS.get(status, str(status))
