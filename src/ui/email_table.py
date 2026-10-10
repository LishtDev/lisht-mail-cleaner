"""Tableau des messages candidats : tri, recherche, filtres, selection.

Le tableau ne modifie jamais Gmail : il ne fait qu'afficher et permettre
la selection, qui sera confirmee plus tard (phase 6).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from src.core.models import Candidate, Recommendation
from src.ui.labels import category_label, protection_label, recommendation_label
from src.utils.dates import format_for_display

COLUMNS = [
    "Sel.",
    "Date",
    "Expediteur",
    "Objet",
    "Categorie IA",
    "Confiance",
    "Protection",
    "Recommandation",
    "Justification",
]

LOCK_TEXT = "\U0001f512"


class EmailTableWidget(QTableWidget):
    """Tableau triable et filtrable des candidats."""

    selection_changed = Signal()
    preview_requested = Signal(object)

    def __init__(self, tz_name: str = "UTC") -> None:
        super().__init__(0, len(COLUMNS))
        self.tz_name = tz_name
        self._candidates: list[Candidate] = []
        self.setHorizontalHeaderLabels(COLUMNS)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        self.itemChanged.connect(self._on_item_changed)
        self.doubleClicked.connect(self._on_double_clicked)

    def set_candidates(self, candidates: list[Candidate]) -> None:
        self.setSortingEnabled(False)
        self.blockSignals(True)
        self.setRowCount(0)
        self._candidates = candidates
        for candidate in candidates:
            self._add_row(candidate)
        self.blockSignals(False)
        self.setSortingEnabled(True)
        self.selection_changed.emit()

    def _add_row(self, candidate: Candidate) -> None:
        row = self.rowCount()
        self.insertRow(row)
        message = candidate.message
        eligible = candidate.is_eligible

        select_item = QTableWidgetItem()
        select_item.setData(Qt.ItemDataRole.UserRole, candidate)
        if eligible:
            select_item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            select_item.setCheckState(
                Qt.CheckState.Checked if candidate.selected else Qt.CheckState.Unchecked
            )
        else:
            select_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            select_item.setText(LOCK_TEXT)
            select_item.setToolTip(candidate.exclusion_reason or "Message protege")
        self.setItem(row, 0, select_item)

        values = [
            format_for_display(message.date, self.tz_name),
            message.sender or message.sender_email or "(inconnu)",
            message.subject or "(sans objet)",
            category_label(candidate.classification.category if candidate.classification else None),
            f"{candidate.classification.confidence:.2f}" if candidate.classification else "-",
            protection_label(candidate.protection),
            recommendation_label(
                candidate.classification.recommendation if candidate.classification else None
            ),
            (candidate.classification.justification if candidate.classification else candidate.exclusion_reason),
        ]
        for offset, value in enumerate(values, start=1):
            item = QTableWidgetItem(str(value))
            item.setData(Qt.ItemDataRole.UserRole, candidate)
            self.setItem(row, offset, item)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        candidate = item.data(Qt.ItemDataRole.UserRole)
        if candidate is None or not candidate.is_eligible:
            return
        candidate.selected = item.checkState() == Qt.CheckState.Checked
        self.selection_changed.emit()

    def _on_double_clicked(self, index) -> None:
        candidate = index.data(Qt.ItemDataRole.UserRole)
        if candidate is None and 0 <= index.row() < len(self._candidates):
            candidate = self._candidates[index.row()]
        if candidate is not None:
            self.preview_requested.emit(candidate)

    def check_all(self, checked: bool) -> None:
        self.blockSignals(True)
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item is None:
                continue
            candidate = item.data(Qt.ItemDataRole.UserRole)
            if candidate is not None and candidate.is_eligible:
                item.setCheckState(
                    Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                )
                candidate.selected = checked
        self.blockSignals(False)
        self.selection_changed.emit()

    def selected_candidates(self) -> list[Candidate]:
        return [c for c in self._candidates if c.selected and c.is_eligible]

    def all_candidates(self) -> list[Candidate]:
        return list(self._candidates)

    def apply_filters(
        self,
        search: str = "",
        category: str = "",
        protection: str = "",
        recommendation: str = "",
        only_candidates: bool = False,
    ) -> int:
        """Masque les lignes ne correspondant pas aux filtres. Retourne le nombre visible."""
        search = search.strip().lower()
        visible = 0
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            candidate = item.data(Qt.ItemDataRole.UserRole) if item else None
            if candidate is None:
                self.setRowHidden(row, True)
                continue
            match = True
            if search:
                haystack = " ".join(
                    [
                        candidate.message.subject or "",
                        candidate.message.sender or "",
                        candidate.message.sender_email or "",
                    ]
                ).lower()
                match = search in haystack
            if match and category:
                match = category_label(
                    candidate.classification.category if candidate.classification else None
                ) == category
            if match and protection:
                match = protection_label(candidate.protection) == protection
            if match and recommendation:
                match = (
                    recommendation_label(
                        candidate.classification.recommendation
                        if candidate.classification
                        else None
                    )
                    == recommendation
                )
            if match and only_candidates:
                eligible = candidate.is_eligible
                is_delete = (
                    candidate.classification is not None
                    and candidate.classification.recommendation
                    == Recommendation.DELETE_CANDIDATE
                )
                match = eligible and is_delete
            self.setRowHidden(row, not match)
            if match:
                visible += 1
        return visible
