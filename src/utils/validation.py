"""Validation des entrees utilisateur (adresses, seuils, configuration)."""

from __future__ import annotations

import re

# Regex volontairement simple et prudente : suffit pour valider une adresse
# de contact protege, sans tenter une conformite RFC complete.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

VALID_AGE_MONTHS = (1, 2, 3, 6, 12)


def is_valid_email(address: str) -> bool:
    """Indique si la chaine ressemble a une adresse e-mail valide."""
    if not address:
        return False
    return bool(_EMAIL_RE.match(address.strip()))


def normalize_email(address: str) -> str:
    """Normalise une adresse pour comparaison (minuscules, sans espaces)."""
    return address.strip().lower()


def extract_email(raw_sender: str) -> str:
    """Extrait l'adresse e-mail d'un en-tete du type 'Nom <adresse@ex.com>'.

    Retourne une chaine vide si aucune adresse n'est identifiable de
    facon fiable (l'appelant doit alors appliquer le principe de prudence).
    """
    if not raw_sender:
        return ""
    match = re.search(r"<([^>]+)>", raw_sender)
    candidate = match.group(1) if match else raw_sender
    candidate = candidate.strip()
    return candidate if is_valid_email(candidate) else ""


def validate_age_months(value: int) -> int:
    """Valide un seuil d'anciennete en mois ; leve ValueError sinon."""
    if value <= 0:
        raise ValueError("Le seuil d'anciennete doit etre un entier positif.")
    return value


def validate_max_delete(value: int) -> int:
    """Valide la limite de suppression par operation."""
    if value <= 0:
        raise ValueError("La limite de suppression doit etre positive.")
    return value


def mask_email(address: str) -> str:
    """Masque partiellement une adresse (pour affichage et rapports)."""
    if not address or "@" not in address:
        return address or "(inconnu)"
    local, domain = address.split("@", 1)
    if len(local) <= 2:
        masked_local = (local[0] + "*") if local else "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"
