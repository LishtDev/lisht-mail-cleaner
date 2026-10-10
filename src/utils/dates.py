"""Utilitaires de dates et de calcul d'anciennete.

Point cle : deux mois calendaires ne correspondent pas a 60 jours.
Le calcul ci-dessous gere correctement les fins de mois et les annees
bissextiles, et travaille toujours sur des datetimes conscients du
fuseau horaire pour eviter les comparaisons incoherentes.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Seuils d'anciennete proposes dans l'interface (section 6).
AGE_OPTIONS_MONTHS = (1, 2, 3, 6, 12)
DEFAULT_AGE_MONTHS = 2


def get_zoneinfo(name: str) -> ZoneInfo:
    """Retourne un ZoneInfo, ou UTC si le fuseau est inconnu."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def last_day_of_month(year: int, month: int) -> int:
    """Nombre de jours du mois indique (gere les annees bissextiles)."""
    return calendar.monthrange(year, month)[1]


def subtract_months(moment: datetime, months: int) -> datetime:
    """Soustrait des mois calendaires a un datetime, en conservant le fuseau.

    Si le jour n'existe pas dans le mois cible (ex. 31 mars -> fevrier),
    on retombe sur le dernier jour valide du mois cible.
    """
    if months < 0:
        raise ValueError("months doit etre positif")

    total = (moment.year * 12 + (moment.month - 1)) - months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    day = min(moment.day, last_day_of_month(year, month))
    return moment.replace(year=year, month=month, day=day)


def compute_cutoff(now: datetime, months: int, tz_name: str = "UTC") -> datetime:
    """Calcule la date limite appliquee.

    Un message est candidat s'il est STRICTEMENT anterieur a cette date.
    """
    zone = get_zoneinfo(tz_name)
    reference = now.astimezone(zone)
    return subtract_months(reference, months)


def is_older_than_cutoff(message_date: datetime | None, cutoff: datetime) -> bool:
    """Indique si un message est strictement anterieur a la date limite."""
    if message_date is None:
        return False
    aware = to_aware(message_date, cutoff.tzinfo)
    return aware < cutoff


def to_aware(moment: datetime, tz: ZoneInfo | timezone | None = None) -> datetime:
    """Rend un datetime conscient du fuseau, sans changer l'instant."""
    if moment.tzinfo is not None:
        return moment
    return moment.replace(tzinfo=tz or timezone.utc)


def parse_gmail_date(raw: str | None, tz_name: str = "UTC") -> datetime | None:
    """Convertit l'en-tete Date d'un message Gmail en datetime conscient.

    Utilise le format RFC 2822 renvoye par Gmail sur l'en-tete `Date`.
    Retourne None si la valeur est absente ou non analysable.
    """
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=get_zoneinfo(tz_name))
    return parsed


def format_for_display(moment: datetime | None, tz_name: str = "UTC") -> str:
    """Formate une date pour l'interface, dans le fuseau demande."""
    if moment is None:
        return "-"
    return moment.astimezone(get_zoneinfo(tz_name)).strftime("%Y-%m-%d %H:%M")
