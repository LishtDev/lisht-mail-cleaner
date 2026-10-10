"""Configuration de la journalisation et protection des donnees sensibles.

Objectif (section 15) : ne jamais enregistrer de jetons OAuth, de corps
d'e-mail, ni d'autres secrets. Un filtre masque les motifs sensibles
avant que les messages ne soient ecrits sur disque.
"""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Motifs de secrets a masquer dans les journaux.
_SECRET_PATTERNS = (
    re.compile(r"(ya29\.[A-Za-z0-9_\-\.]+)"),          # jeton d'acces Google
    re.compile(r"(1//[A-Za-z0-9_\-\.]+)"),               # jeton de rafraichissement
    re.compile(r"(?i)(access_token\"?\s*[:=]\s*\"?)([^\"\s,}]+)"),
    re.compile(r"(?i)(refresh_token\"?\s*[:=]\s*\"?)([^\"\s,}]+)"),
    re.compile(r"(?i)(client_secret\"?\s*[:=]\s*\"?)([^\"\s,}]+)"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)(\S+)"),
)

_REDACTED = "[MASQUE]"


def redact(text: str) -> str:
    """Masque les motifs sensibles dans une chaine destinee au journal."""
    if not text:
        return text
    result = text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 2:
            result = pattern.sub(lambda m: m.group(1) + _REDACTED, result)
        else:
            result = pattern.sub(_REDACTED, result)
    return result


class RedactingFilter(logging.Filter):
    """Filtre qui expurge les secrets de tous les enregistrements."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
            redacted = redact(message)
            if redacted != message:
                record.msg = redacted
                record.args = ()
        except Exception:  # pragma: no cover - securite avant tout
            record.msg = "[message de journal non formattable - masque]"
            record.args = ()
        return True


def configure_logging(
    log_dir: Path,
    level: str = "INFO",
    console: bool = True,
) -> logging.Logger:
    """Configure le logger racine avec un fichier rotatif et la console."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("lisht")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    redactor = RedactingFilter()

    file_handler = RotatingFileHandler(
        log_dir / "lisht_mail_cleaner.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redactor)
    logger.addHandler(file_handler)

    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        stream.addFilter(redactor)
        logger.addHandler(stream)

    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger enfant du logger applicatif."""
    return logging.getLogger("lisht").getChild(name)
