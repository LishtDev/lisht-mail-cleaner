"""Tests de la journalisation : aucune fuite de secret."""

from __future__ import annotations

import logging

from src.utils.logging_config import RedactingFilter, redact


def test_redact_google_access_token():
    text = "reponse: ya29.a0AfH6SMBexampleTOKEN123 fin"
    assert "ya29.a0" not in redact(text)
    assert "[MASQUE]" in redact(text)


def test_redact_refresh_token():
    text = "refresh_token=1//0abcDEF_token_value"
    result = redact(text)
    assert "0abcDEF" not in result


def test_redact_authorization_header():
    text = "Authorization: Bearer ya29.somethingSecret"
    result = redact(text)
    assert "somethingSecret" not in result


def test_redact_keeps_normal_text():
    text = "Analyse terminee pour 42 messages."
    assert redact(text) == text


def test_filter_scrubs_record_before_handlers():
    records: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    logger = logging.getLogger("test.redaction")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.addFilter(RedactingFilter())
    logger.addHandler(Capture())
    logger.propagate = False

    logger.info("Jeton recu : ya29.a0AfH6SMBsecretVALUE")

    assert records
    assert "ya29.a0" not in records[0]
    assert "[MASQUE]" in records[0]
