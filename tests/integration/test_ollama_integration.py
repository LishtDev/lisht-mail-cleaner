"""Tests d'integration opt-in du moteur IA local (Ollama).

Exclus par defaut. Pour les executer :

    pytest -m integration

Ces tests ne contactent jamais Gmail et ne suppriment rien.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.ai.classifier import AIClassifier
from src.ai.local_model import LocalModel
from src.core.models import EmailMessage

pytestmark = pytest.mark.integration

MODEL_NAME = "qwen2.5:1.5b-instruct"


@pytest.fixture(scope="module")
def local_model():
    model = LocalModel(MODEL_NAME)
    status = model.check_status()
    if not status.ready:
        pytest.skip(f"Moteur/model IA local indisponible : {status.error}")
    return model


def test_local_model_status_ready(local_model):
    assert local_model.check_status().ready is True


def test_ai_classifies_promotional_email(local_model):
    message = EmailMessage(
        id="x",
        subject="Offre exceptionnelle -70% sur tout le site",
        sender="Promo <promo@shop.example>",
        sender_email="promo@shop.example",
        date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        snippet="Cliquez pour profiter de la reduction. Se desabonner en bas.",
    )
    classification = AIClassifier(local_model).classify(message)
    assert classification.source == "ollama"
    assert classification.category.value == "publicite_promotion"
