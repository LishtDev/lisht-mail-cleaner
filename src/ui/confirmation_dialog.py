"""Fenetre de confirmation avant toute suppression (section 12).

Aucune action destructive ne peut se produire sans passer par cette
fenetre : elle exige une validation humaine, et pour la suppression
definitive, la saisie d'une phrase exacte.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from src.services.cleanup_service import REQUIRED_DELETE_PHRASE, CleanupMode
from src.utils.dates import format_for_display
from src.utils.validation import mask_email


class ConfirmationDialog(QDialog):
    """Confirmation explicite d'une operation de nettoyage."""

    def __init__(
        self,
        mode: CleanupMode,
        account: str,
        count: int,
        protected_count: int,
        cutoff,
        dry_run: bool,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self.dry_run = dry_run
        self.setWindowTitle("Confirmation requise")
        self.resize(520, 320)
        self._build(account, count, protected_count, cutoff)

    def _build(self, account: str, count: int, protected_count: int, cutoff) -> None:
        layout = QVBoxLayout(self)

        is_delete = self.mode == CleanupMode.DELETE
        headline = (
            "Suppression DEFINITIVE" if is_delete else "Mise a la corbeille"
        )
        title = QLabel(f"<b>{headline}</b>")
        layout.addWidget(title)

        cutoff_text = format_for_display(cutoff) if cutoff else "-"
        summary = QLabel(
            f"<b>Compte :</b> {mask_email(account)}<br>"
            f"<b>Messages selectionnes :</b> {count}<br>"
            f"<b>Messages proteges (exclus) :</b> {protected_count}<br>"
            f"<b>Date limite appliquee :</b> {cutoff_text}<br>"
            f"<b>Mode :</b> {'SIMULATION (aucun effet)' if self.dry_run else 'REEL'}"
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        if is_delete and not self.dry_run:
            warning = QLabel(
                "La suppression definitive est <b>irreversible</b>. "
                "L'application ne pourra pas restaurer ces messages."
            )
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #e03131; font-weight: bold;")
            layout.addWidget(warning)

            prompt = QLabel(f"Saisissez : <b>{REQUIRED_DELETE_PHRASE}</b>")
            layout.addWidget(prompt)
            self.phrase_edit = QLineEdit()
            self.phrase_edit.setPlaceholderText(REQUIRED_DELETE_PHRASE)
            self.phrase_edit.textChanged.connect(self._update_buttons)
            layout.addWidget(self.phrase_edit)
        else:
            self.phrase_edit = None
            note = QLabel(
                "La mise a la corbeille est reversible : les messages pourront etre "
                "restaures depuis Gmail."
            )
            note.setWordWrap(True)
            layout.addWidget(note)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("Supprimer definitivement" if is_delete else "Mettre a la corbeille")
        if is_delete:
            ok_button.setObjectName("danger")
        else:
            ok_button.setObjectName("primary")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self._update_buttons()

    def _update_buttons(self) -> None:
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if self.mode == CleanupMode.DELETE and not self.dry_run:
            valid = self.phrase_edit is not None and (
                self.phrase_edit.text().strip() == REQUIRED_DELETE_PHRASE
            )
            ok_button.setEnabled(valid)
        else:
            ok_button.setEnabled(True)

    def phrase(self) -> str:
        return self.phrase_edit.text() if self.phrase_edit is not None else ""
