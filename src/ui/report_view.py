"""Ecran Rapport : synthese du dernier scan et exports CSV/JSON."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.services.report_service import build_report, write_csv, write_json
from src.utils.dates import compute_cutoff, get_zoneinfo
from src.utils.validation import mask_email
from datetime import datetime


class ReportView(QWidget):
    """Genere et exporte un rapport a partir du dernier scan disponible."""

    def __init__(
        self,
        settings,
        last_result_provider,
        connection_service=None,
        tz_name: str = "UTC",
    ) -> None:
        super().__init__()
        self.settings = settings
        self.last_result_provider = last_result_provider
        self.connection_service = connection_service
        self.tz_name = tz_name
        self._report: dict | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("Rapport")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("pageSubtitle")
        layout.addWidget(self.subtitle)

        actions = QHBoxLayout()
        generate_button = QPushButton("Generer le rapport")
        generate_button.setObjectName("primary")
        generate_button.clicked.connect(self.refresh)
        self.json_button = QPushButton("Exporter en JSON")
        self.json_button.clicked.connect(self._export_json)
        self.csv_button = QPushButton("Exporter en CSV")
        self.csv_button.clicked.connect(self._export_csv)
        actions.addWidget(generate_button)
        actions.addWidget(self.json_button)
        actions.addWidget(self.csv_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setObjectName("reportSummary")
        layout.addWidget(self.summary, stretch=1)

    def refresh(self) -> None:
        scan = self.last_result_provider() if self.last_result_provider else None
        account = (
            self.connection_service.account_email if self.connection_service else ""
        )
        cutoff = compute_cutoff(
            datetime.now(get_zoneinfo(self.tz_name)),
            self.settings.age_months,
            self.tz_name,
        )
        self._report = build_report(
            scan,
            account=account,
            age_months=self.settings.age_months,
            cutoff=cutoff,
            tz_name=self.tz_name,
        )
        self._render()
        self._update_buttons()

    def _update_buttons(self) -> None:
        has_data = bool(self._report and self._report.get("messages"))
        self.json_button.setEnabled(has_data)
        self.csv_button.setEnabled(has_data)

    def _render(self) -> None:
        if not self._report:
            return
        report = self._report
        if not report["messages"]:
            self.subtitle.setText(
                "Aucune analyse disponible. Lancez une analyse depuis l'ecran "
                "\"Analyse des e-mails\" pour alimenter le rapport."
            )
        else:
            self.subtitle.setText(
                f"Rapport base sur {report['messages_analyses']} message(s) analyse(s). "
                "Le corps des e-mails n'est jamais inclus."
            )
        lines = [
            f"Compte : {mask_email(report['compte'])}",
            f"Genere le : {report['genere_le']}",
            f"Seuil d'anciennete : {report['seuil_mois']} mois",
            f"Date limite : {report['date_limite']}",
            f"Mode : {'simulation' if report['mode_simulation'] else 'reel'}",
            "",
            f"Messages recuperes : {report['messages_recuperes']}",
            f"Messages exclus : {report['messages_exclus']}",
            f"Messages analyses : {report['messages_analyses']}",
            f"Messages proteges : {report['messages_proteges']}",
            f"Candidats : {report['candidats']}",
            f"Messages selectionnes : {report['messages_selectionnes']}",
            f"Suppressions reussies : {report['suppressions_reussies']}",
            f"Messages en corbeille : {report['messages_en_corbeille']}",
            f"Echecs : {report['echecs']}",
            "",
            report["note_espace_disque"],
        ]
        self.summary.setPlainText("\n".join(lines))

    def _export_json(self) -> None:
        self._export("json")

    def _export_csv(self) -> None:
        self._export("csv")

    def _export(self, kind: str) -> None:
        if not self._report:
            return
        default_name = f"rapport_lisht_mail_cleaner.{kind}"
        filters = "JSON (*.json)" if kind == "json" else "CSV (*.csv)"
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter le rapport", str(Path.home() / default_name), filters
        )
        if not path:
            return
        try:
            if kind == "json":
                write_json(self._report, path)
            else:
                write_csv(self._report, path)
        except OSError as exc:
            QMessageBox.critical(self, "Export impossible", f"Erreur d'ecriture : {exc}")
            return
        QMessageBox.information(self, "Export reussi", f"Rapport enregistre dans :\n{path}")
