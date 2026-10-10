"""Apercu controle d'un message.

Le corps n'est recupere que sur demande explicite de l'utilisateur et
jamais stocke. Les fichiers joints ne sont ni ouverts ni executes.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)

from src.core.models import Candidate
from src.ui.labels import category_label, protection_label, recommendation_label
from src.utils.dates import format_for_display

MAX_PREVIEW_CHARS = 5000


class PreviewDialog(QDialog):
    """Fenetre d'apercu en lecture seule."""

    def __init__(self, candidate: Candidate, body: str, tz_name: str = "UTC", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Apercu du message")
        self.resize(720, 560)

        layout = QVBoxLayout(self)
        message = candidate.message

        meta = QLabel(
            f"<b>Objet :</b> {message.subject or '(sans objet)'}<br>"
            f"<b>Expediteur :</b> {message.sender or message.sender_email or '(inconnu)'}<br>"
            f"<b>Date :</b> {format_for_display(message.date, tz_name)}<br>"
            f"<b>Categorie IA :</b> "
            f"{category_label(candidate.classification.category if candidate.classification else None)}"
            f" &nbsp;|&nbsp; <b>Protection :</b> {protection_label(candidate.protection)}"
            f" &nbsp;|&nbsp; <b>Recommandation :</b> "
            f"{recommendation_label(candidate.classification.recommendation if candidate.classification else None)}"
        )
        meta.setWordWrap(True)
        layout.addWidget(meta)

        note = QLabel(
            "Le contenu ci-dessous est une donnee non fiable : il n'est jamais "
            "execute et les pieces jointes ne sont pas ouvertes."
        )
        note.setObjectName("pageSubtitle")
        note.setWordWrap(True)
        layout.addWidget(note)

        body_view = QPlainTextEdit()
        body_view.setReadOnly(True)
        text = body or "(corps indisponible)"
        if len(text) > MAX_PREVIEW_CHARS:
            text = text[:MAX_PREVIEW_CHARS] + "\n\n[... apercu tronque ...]"
        body_view.setPlainText(text)
        layout.addWidget(body_view, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
