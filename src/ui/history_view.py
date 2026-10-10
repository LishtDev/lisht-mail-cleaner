"""Ecran Historique : trace locale des scans et des nettoyages."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.utils.dates import format_for_display
from src.utils.validation import mask_email

KIND_LABELS = {
    "scan": "Analyse",
    "scan_auto": "Analyse planifiee",
    "nettoyage_trash": "Corbeille",
    "nettoyage_delete": "Suppression definitive",
}

COLUMNS = [
    ("date", "Date"),
    ("kind", "Type"),
    ("account", "Compte"),
    ("analyzed", "Analyses"),
    ("protected", "Proteges"),
    ("candidates", "Candidats"),
    ("selected", "Selectionnes"),
    ("deleted", "Supprimes"),
    ("failed", "Echecs"),
    ("mode", "Mode"),
    ("status", "Statut"),
]


class HistoryView(QWidget):
    """Tableau de l'historique des operations locales."""

    def __init__(self, settings_provider, operation_repo, tz_name: str = "UTC") -> None:
        super().__init__()
        self.settings_provider = settings_provider
        self.operation_repo = operation_repo
        self.tz_name = tz_name
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("Historique")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("pageSubtitle")
        layout.addWidget(self.subtitle)

        actions = QHBoxLayout()
        refresh_button = QPushButton("Rafraichir")
        refresh_button.clicked.connect(self.refresh)
        actions.addWidget(refresh_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _, label in COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, stretch=1)

    def refresh(self) -> None:
        records = []
        if self.operation_repo is not None:
            records = self.operation_repo.list_recent(100)
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            values = self._row_values(record)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                self.table.setItem(row, column, item)
        self.subtitle.setText(
            f"{len(records)} operation(s) enregistree(s). "
            "Aucun contenu d'e-mail n'est conserve dans cet historique."
        )

    def _row_values(self, record: dict) -> list[str]:
        mode = "Simulation" if record.get("dry_run") else "Reel"
        kind = KIND_LABELS.get(record.get("kind", ""), record.get("kind", ""))
        return [
            self._format_timestamp(record.get("started_at")),
            kind,
            mask_email(record.get("account") or ""),
            record.get("analyzed", 0),
            record.get("protected", 0),
            record.get("candidates", 0),
            record.get("selected", 0),
            record.get("deleted", 0),
            record.get("failed", 0),
            mode,
            record.get("status", ""),
        ]

    def _format_timestamp(self, raw: str | None) -> str:
        if not raw:
            return "-"
        try:
            moment = datetime.fromisoformat(raw)
        except ValueError:
            return raw
        return format_for_display(moment, self.tz_name)
