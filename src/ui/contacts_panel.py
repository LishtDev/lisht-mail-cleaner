"""Panneau de gestion des contacts proteges (section 9.2).

Permet d'ajouter, modifier, supprimer et importer des adresses. Toute
adresse de cette liste est exclue des candidats a la suppression.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.utils.validation import is_valid_email

COLUMNS = ["Adresse", "Libelle"]


class ContactsPanel(QWidget):
    """Liste editable des contacts proteges."""

    def __init__(self, contact_repo, parent=None) -> None:
        super().__init__(parent)
        self.contact_repo = contact_repo
        self._build()
        self.reload()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Contacts proteges")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        note = QLabel(
            "Les messages provenant de ces adresses ne seront jamais proposes a la suppression."
        )
        note.setObjectName("pageSubtitle")
        note.setWordWrap(True)
        layout.addWidget(note)

        add_row = QHBoxLayout()
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("adresse@exemple.com")
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Libelle (optionnel)")
        add_button = QPushButton("Ajouter")
        add_button.setObjectName("primary")
        add_button.clicked.connect(self._on_add)
        add_row.addWidget(self.email_edit, stretch=2)
        add_row.addWidget(self.label_edit, stretch=1)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self.table, stretch=1)

        actions = QHBoxLayout()
        edit_button = QPushButton("Modifier")
        edit_button.clicked.connect(self._on_edit)
        delete_button = QPushButton("Supprimer")
        delete_button.setObjectName("danger")
        delete_button.clicked.connect(self._on_delete)
        import_button = QPushButton("Importer depuis un fichier...")
        import_button.clicked.connect(self._on_import)
        actions.addWidget(edit_button)
        actions.addWidget(delete_button)
        actions.addWidget(import_button)
        actions.addStretch(1)
        layout.addLayout(actions)

    def reload(self) -> None:
        contacts = self.contact_repo.list_all()
        self.table.setRowCount(0)
        for contact in contacts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            email_item = QTableWidgetItem(contact.email)
            email_item.setData(Qt.ItemDataRole.UserRole, contact.id)
            self.table.setItem(row, 0, email_item)
            self.table.setItem(row, 1, QTableWidgetItem(contact.label))

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_add(self) -> None:
        email = self.email_edit.text().strip()
        if not is_valid_email(email):
            QMessageBox.warning(self, "Adresse invalide", f"« {email} » n'est pas une adresse valide.")
            return
        self.contact_repo.add(email, self.label_edit.text())
        self.email_edit.clear()
        self.label_edit.clear()
        self.reload()

    def _on_edit(self) -> None:
        contact_id = self._selected_id()
        if contact_id is None:
            return
        row = self.table.currentRow()
        current_email = self.table.item(row, 0).text()
        current_label = self.table.item(row, 1).text()
        new_email, ok = QInputDialog.getText(self, "Modifier", "Adresse :", text=current_email)
        if not ok:
            return
        new_label, ok = QInputDialog.getText(self, "Modifier", "Libelle :", text=current_label)
        if not ok:
            return
        try:
            self.contact_repo.update(contact_id, new_email, new_label)
        except ValueError as exc:
            QMessageBox.warning(self, "Adresse invalide", str(exc))
            return
        self.reload()

    def _on_delete(self) -> None:
        contact_id = self._selected_id()
        if contact_id is None:
            return
        answer = QMessageBox.question(
            self, "Supprimer", "Retirer ce contact de la liste protegee ?"
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.contact_repo.delete(contact_id)
            self.reload()

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer des contacts",
            "",
            "Fichiers texte (*.txt *.csv);;Tous les fichiers (*)",
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
        except OSError as exc:
            QMessageBox.critical(self, "Import impossible", str(exc))
            return

        addresses = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.replace(";", ",").split(",")
            for part in parts:
                part = part.strip()
                if is_valid_email(part):
                    addresses.append(part)
        added = self.contact_repo.import_many(addresses)
        self.reload()
        QMessageBox.information(self, "Import termine", f"{added} adresse(s) ajoutee(s).")
