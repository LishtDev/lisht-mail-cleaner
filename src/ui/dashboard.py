"""Tableau de bord : vue d'ensemble et connexion Gmail (section 10)."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.services.connection_service import ConnectionService
from src.ui.workers import TaskRunner
from src.utils.dates import format_for_display, get_zoneinfo


class StatCard(QFrame):
    """Petite carte affichant un intitule et une valeur."""

    def __init__(self, title: str, value: str = "-", accent: bool = False) -> None:
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(84)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        if accent:
            self.value_label.setStyleSheet("color: #22b8cf;")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class DashboardView(QWidget):
    """Affiche les indicateurs et permet de connecter/deconnecter Gmail."""

    def __init__(
        self,
        settings,
        connection_service: ConnectionService | None = None,
        local_model=None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.connection_service = connection_service
        self.local_model = local_model
        self._task_runner = TaskRunner(self)
        self._task_runner.finished.connect(self._on_connect_finished)
        self._task_runner.failed.connect(self._on_connect_failed)
        self._ai_runner = TaskRunner(self)
        self._ai_runner.finished.connect(self._on_ai_status)
        self._ai_runner.failed.connect(self._on_ai_error)
        self._build()
        self._sync_connection_display()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Tableau de bord")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Etat de la connexion Gmail, du moteur IA local et des derniers scans."
        )
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(subtitle)

        buttons = QHBoxLayout()
        self.connect_button = QPushButton("Connecter Gmail")
        self.connect_button.setObjectName("primary")
        self.connect_button.clicked.connect(self._on_connect_clicked)
        self.disconnect_button = QPushButton("Se deconnecter")
        self.disconnect_button.clicked.connect(self._on_disconnect_clicked)
        self.ai_button = QPushButton("Verifier le moteur IA")
        self.ai_button.clicked.connect(self._on_check_ai_clicked)
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.disconnect_button)
        buttons.addWidget(self.ai_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)

        self.card_account = StatCard("Compte Gmail connecte", "Non connecte", accent=True)
        self.card_connection = StatCard("Etat de la connexion", "Deconnecte")
        self.card_last_scan = StatCard("Date du dernier scan", "-")
        self.card_threshold = StatCard("Seuil d'anciennete", f"{self.settings.age_months} mois")
        self.card_analyzed = StatCard("Messages analyses", "0")
        self.card_protected = StatCard("Messages proteges", "0")
        self.card_candidates = StatCard("Candidats a la suppression", "0", accent=True)
        self.card_deleted = StatCard("Suppressions realisees", "0")
        self.card_ai = StatCard("Moteur IA local", "Non verifie")
        self.card_next_run = StatCard("Prochain nettoyage planifie", "Non planifie")

        cards = [
            self.card_account,
            self.card_connection,
            self.card_last_scan,
            self.card_threshold,
            self.card_analyzed,
            self.card_protected,
            self.card_candidates,
            self.card_deleted,
            self.card_ai,
            self.card_next_run,
        ]
        for index, card in enumerate(cards):
            grid.addWidget(card, index // 2, index % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        self.meta = QLabel("")
        self.meta.setObjectName("pageSubtitle")
        self.meta.setWordWrap(True)
        layout.addWidget(self.meta)
        layout.addStretch(1)
        self._refresh_meta()
        if self.local_model is not None:
            QTimer.singleShot(300, self._on_check_ai_clicked)

    def _refresh_meta(self) -> None:
        self.meta.setText(
            f"Fuseau horaire : {self.settings.timezone}   |   "
            f"Mode simulation : {'active' if self.settings.dry_run else 'desactive'}   |   "
            f"Limite par operation : {self.settings.max_delete_per_run} messages   |   "
            f"Heure locale : "
            f"{format_for_display(datetime.now(get_zoneinfo(self.settings.timezone)), self.settings.timezone)}"
        )

    def stop_background(self) -> None:
        """Arrete proprement les taches d'arriere-plan a la fermeture."""
        self._task_runner.wait(2000)
        self._ai_runner.wait(2000)

    def _sync_connection_display(self) -> None:
        connected = bool(
            self.connection_service and self.connection_service.is_connected
        )
        if connected:
            self.card_account.set_value(self.connection_service.account_email)
            self.card_connection.set_value("Connecte")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
        else:
            self.card_account.set_value("Non connecte")
            self.card_connection.set_value("Deconnecte")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)

    def _on_connect_clicked(self) -> None:
        if self.connection_service is None:
            QMessageBox.warning(
                self,
                "Service indisponible",
                "Le service de connexion n'est pas initialise.",
            )
            return
        self.connect_button.setEnabled(False)
        self.connect_button.setText("Connexion en cours...")
        self.card_connection.set_value("Verification du navigateur...")
        self._task_runner.run(self.connection_service.connect)

    def _on_connect_finished(self, result: object) -> None:
        self.connect_button.setText("Connecter Gmail")
        self._sync_connection_display()
        email = ""
        if isinstance(result, dict):
            email = result.get("emailAddress", "")
        QMessageBox.information(
            self,
            "Connexion reussie",
            f"Compte connecte : {email or 'inconnu'}",
        )

    def _on_connect_failed(self, message: str) -> None:
        self.connect_button.setText("Connecter Gmail")
        self._sync_connection_display()
        QMessageBox.critical(self, "Echec de la connexion", message)

    def _on_check_ai_clicked(self) -> None:
        if self.local_model is None:
            QMessageBox.information(
                self, "IA locale", "Aucun moteur IA n'est configure."
            )
            return
        if self._ai_runner.is_running():
            return
        self.ai_button.setEnabled(False)
        self.card_ai.set_value("Verification...")
        self._ai_runner.run(self.local_model.check_status)

    def _on_ai_status(self, status: object) -> None:
        self.ai_button.setEnabled(True)
        if getattr(status, "ready", False):
            self.card_ai.set_value(f"Pret ({getattr(status, 'model_name', '')})")
        elif getattr(status, "engine_available", False):
            self.card_ai.set_value("Modele absent")
        else:
            self.card_ai.set_value("Indisponible")

    def _on_ai_error(self, message: str) -> None:
        self.ai_button.setEnabled(True)
        self.card_ai.set_value("Erreur")

    def _on_disconnect_clicked(self) -> None:
        if self.connection_service is None:
            return
        answer = QMessageBox.question(
            self,
            "Se deconnecter",
            "Supprimer les jetons locaux et se deconnecter du compte Gmail ?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.connection_service.disconnect(revoke=False)
            self._sync_connection_display()
