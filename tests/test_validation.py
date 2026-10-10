"""Tests de validation des entrees."""

from __future__ import annotations

import pytest

from src.utils.validation import (
    extract_email,
    is_valid_email,
    mask_email,
    normalize_email,
    validate_age_months,
)


@pytest.mark.parametrize(
    "address,expected",
    [
        ("contact@example.com", True),
        ("prenom.nom+tag@sous.domaine.fr", True),
        ("invalide", False),
        ("invalide@", False),
        ("@domaine.com", False),
        ("", False),
    ],
)
def test_is_valid_email(address, expected):
    assert is_valid_email(address) is expected


def test_normalize_email():
    assert normalize_email("  User@Example.COM ") == "user@example.com"


def test_extract_email_from_header():
    assert extract_email("Alice <alice@example.com>") == "alice@example.com"
    assert extract_email("bob@example.com") == "bob@example.com"


def test_extract_email_unreliable_returns_empty():
    assert extract_email("Nom sans adresse") == ""
    assert extract_email("") == ""


def test_validate_age_months():
    assert validate_age_months(2) == 2
    with pytest.raises(ValueError):
        validate_age_months(0)


def test_mask_email_hides_local_part():
    assert mask_email("alice@example.com") == "a***e@example.com"
    assert mask_email("a@example.com") == "a*@example.com"
    assert mask_email("") == "(inconnu)"
    assert mask_email("sans-arobase") == "sans-arobase"
