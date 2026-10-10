"""Ecran « Analyse des e-mails » : scan, filtres, selection et apercu."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ai.classifier import AIClassifier, RuleBasedClassifier
from src.core.models import Candidate
from src.gmail.email_repository import SearchScope, build_query
from src.services.cleanup_service import (
    CleanupError,
    CleanupMode,
    CleanupResult,
    CleanupService,
    Confirmation,
    LimitExceededError,
)
from src.services.protection_service import ProtectionService
from src.services.scan_service import ScanResult, ScanService
from src.ui.confirmation_dialog import ConfirmationDialog
from src.ui.email_table import EmailTableWidget
from src.ui.labels import CATEGORY_LABELS, PROTECTION_LABELS, RECOMMENDATION_LABELS
from src.ui.preview_dialog import PreviewDialog
from src.ui.workers import ProgressTaskRunner
from src.utils.dates import compute_cutoff, format_for_display, get_zoneinfo
from src.utils.logging_config import get_logger

logger = get_logger("ui.analysis")

SCOPE_OPTIONS = [
    ("Tous les messages (hors corbeille/spam)", SearchScope.ALL_MAIL),
    ("Boite de reception", SearchScope.INBOX),
    ("Messages envoyes", SearchScope.SENT),
    ("Archives (hors boite de reception)", SearchScope.ARCHIVED),
    ("Promotions", SearchScope.PROMOTIONS),
    ("Reseaux sociaux", SearchScope.SOCIAL),
    ("Forums", SearchScope.FORUMS),
    ("Mises a jour", SearchScope.UPDATES),
]


class AnalysisView(QWidget):
    """Construit et affiche la liste des candidats a la suppression."""

    def __init__(
        self,
        settings,
        settings_repo,
        contact_repo,
        connection_service=None,
        local_model=None,
        operation_repo=None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.settings_repo = settings_repo
        self.contact_repo = contact_repo
        self.connection_service = connection_service
        self.local_model = local_model
        self.operation_repo = operation_repo
        self._cancel_requested = False
        self._scheduled = False
        self.last_result: ScanResult | None = None

        self.runner = ProgressTaskRunner(self)
        self.runner.progress.connect(self._on_progress)
        self.runner.finished.connect(self._on_scan_finished)
        self.runner.failed.connect(self._on_scan_failed)

        self.cleanup_runner = ProgressTaskRunner(self)
        self.cleanup_runner.progress.connect(self._on_progress)
        self.cleanup_runner.finished.connect(self._on_cleanup_finished)
        self.cleanup_runner.failed.connect(self._on_cleanup_failed)

        self._build()

    def stop_background(self) -> None:
        """Demande l'annulation du scan et attend la fin du thread."""
        self._cancel_requested = True
        self.runner.wait(3000)
        self.cleanup_runner.wait(3000)

    # --- Construction de l'interface ---

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("Analyse des e-mails")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.subtitle = QLabel("")
        self.subtitle.setObjectName("pageSubtitle")
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)

        controls = QHBoxLayout()
        self.scope_combo = QComboBox()
        for label, scope in SCOPE_OPTIONS:
            self.scope_combo.addItem(label, scope)
        controls.addWidget(QLabel("Perimetre :"))
        controls.addWidget(self.scope_combo, stretch=1)

        self.scan_button = QPushButton("Lancer l'analyse")
        self.scan_button.setObjectName("primary")
        self.scan_button.clicked.connect(self._on_scan_clicked)
        controls.addWidget(self.scan_button)

        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        controls.addWidget(self.cancel_button)
        layout.addLayout(controls)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("pageSubtitle")
        layout.addWidget(self.progress_label)

        # Filtres
        filters = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rechercher (objet, expediteur)...")
        self.search_edit.textChanged.connect(self._apply_filters)
        filters.addWidget(self.search_edit, stretch=2)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Toutes categories", "")
        for label in CATEGORY_LABELS.values():
            self.category_combo.addItem(label, label)
        self.category_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.category_combo, stretch=1)

        self.protection_combo = QComboBox()
        self.protection_combo.addItem("Toutes protections", "")
        for label in PROTECTION_LABELS.values():
            self.protection_combo.addItem(label, label)
        self.protection_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.protection_combo, stretch=1)

        self.reco_combo = QComboBox()
        self.reco_combo.addItem("Toutes recommandations", "")
        for label in RECOMMENDATION_LABELS.values():
            self.reco_combo.addItem(label, label)
        self.reco_combo.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.reco_combo, stretch=1)

        self.only_candidates_check = QCheckBox("Candidats uniquement")
        self.only_candidates_check.stateChanged.connect(self._apply_filters)
        filters.addWidget(self.only_candidates_check)
        layout.addLayout(filters)

        self.table = EmailTableWidget(self._timezone())
        self.table.selection_changed.connect(self._update_summary)
        self.table.preview_requested.connect(self._on_preview)
        layout.addWidget(self.table, stretch=1)

        actions = QHBoxLayout()
        select_all = QPushButton("Tout selectionner")
        select_all.clicked.connect(lambda: self.table.check_all(True))
        deselect_all = QPushButton("Tout deselectionner")
        deselect_all.clicked.connect(lambda: self.table.check_all(False))
        preview_button = QPushButton("Apercu du message")
        preview_button.clicked.connect(self._preview_current_row)
        self.summary = QLabel("")
        actions.addWidget(select_all)
        actions.addWidget(deselect_all)
        actions.addWidget(preview_button)
        actions.addStretch(1)
        actions.addWidget(self.summary)
        layout.addLayout(actions)

        destructive = QHBoxLayout()
        self.trash_button = QPushButton("Mettre a la corbeille (reversible)")
        self.trash_button.setObjectName("primary")
        self.trash_button.clicked.connect(lambda: self._start_cleanup(CleanupMode.TRASH))
        self.delete_button = QPushButton("Supprimer definitivement (irreversible)")
        self.delete_button.setObjectName("danger")
        self.delete_button.clicked.connect(lambda: self._start_cleanup(CleanupMode.DELETE))
        destructive.addWidget(self.trash_button)
        destructive.addWidget(self.delete_button)
        destructive.addStretch(1)
        layout.addLayout(destructive)

        self._refresh_subtitle()

    # --- Utilitaires ---

    def _timezone(self) -> str:
        return self.settings_repo.get("timezone", self.settings.timezone) or self.settings.timezone

    def _age_months(self) -> int:
        return self.settings_repo.get_int("age_months", self.settings.age_months)

    def _refresh_subtitle(self) -> None:
        tz = self._timezone()
        cutoff = compute_cutoff(datetime.now(get_zoneinfo(tz)), self._age_months(), tz)
        dry = "active" if self.settings_repo.get_bool("dry_run", self.settings.dry_run) else "desactive"
        self.subtitle.setText(
            f"Seuil : {self._age_months()} mois calendaires  |  Date limite : "
            f"{format_for_display(cutoff, tz)}  |  Mode simulation : {dry}"
        )

    # --- Scan ---

    def _on_scan_clicked(self) -> None:
        if self.connection_service is None or not self.connection_service.is_connected:
            QMessageBox.warning(
                self,
                "Compte non connecte",
                "Connectez d'abord un compte Gmail depuis le tableau de bord.",
            )
            return
        self._begin_scan(scheduled=False)

    def start_scheduled_scan(self) -> None:
        """Scan planifie en lecture seule (sans boite de dialogue)."""
        if self.connection_service is None or not self.connection_service.is_connected:
            logger.info("Scan planifie ignore : compte non connecte.")
            return
        self._begin_scan(scheduled=True)

    def _begin_scan(self, scheduled: bool) -> None:
        if self.runner.is_running():
            return

        self._scheduled = scheduled
        self._cancel_requested = False
        self.scan_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setVisible(True)
        self.progress_label.setText("Preparation de l'analyse...")

        tz = self._timezone()
        age = self._age_months()
        cutoff = compute_cutoff(datetime.now(get_zoneinfo(tz)), age, tz)
        scope = self.scope_combo.currentData()
        query_spec = build_query([scope], cutoff)
        protected = self.contact_repo.emails()
        account = self.connection_service.account_email

        def task(emit_progress):
            client = self.connection_service.client()
            classifier = RuleBasedClassifier()
            if self.local_model is not None:
                status = self.local_model.check_status()
                if status.ready:
                    classifier = AIClassifier(self.local_model)
            protection = ProtectionService(protected_emails=protected)
            service = ScanService(
                client=client,
                classifier=classifier,
                protection=protection,
                tz_name=tz,
                progress=emit_progress,
                cancel_check=lambda: self._cancel_requested,
            )
            return service.scan(query_spec, account=account)

        self.runner.run(task)

    def _on_cancel_clicked(self) -> None:
        self._cancel_requested = True
        self.progress_label.setText("Interruption demandee...")

    def _on_progress(self, count: int, text: str) -> None:
        self.progress_label.setText(text)

    def _on_scan_finished(self, result: object) -> None:
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(False)
        if not isinstance(result, ScanResult):
            self._on_scan_failed("Resultat d'analyse inattendu.")
            return
        self.last_result = result
        self.table.set_candidates(result.candidates)
        self._apply_filters()
        self._update_summary()
        self._refresh_subtitle()

        kind = "scan_auto" if self._scheduled else "scan"
        self._record_scan(result, kind)
        if self._scheduled:
            logger.info(
                "Scan planifie termine : %s analyses, %s candidats.",
                result.analyzed,
                result.candidate_count,
            )
            return

        message = (
            f"Analyse terminee ({result.classifier_source}).\n"
            f"Messages recuperes : {result.fetched}\n"
            f"Messages dans le perimetre ancien : {result.analyzed}\n"
            f"Messages proteges : {result.protected}\n"
            f"Candidats : {result.candidate_count}"
        )
        if result.errors:
            message += "\n\nErreurs :\n- " + "\n- ".join(result.errors[:10])
        QMessageBox.information(self, "Analyse terminee", message)

    def _record_scan(self, result: ScanResult, kind: str) -> None:
        if self.operation_repo is None:
            return
        from src.database.repositories import OperationRecord

        record = OperationRecord(
            kind=kind,
            account=self.connection_service.account_email if self.connection_service else "",
            age_months=self._age_months(),
            analyzed=result.analyzed,
            excluded=result.excluded,
            protected=result.protected,
            candidates=result.candidate_count,
            dry_run=True,
            status="termine",
        )
        op_id = self.operation_repo.create(record)
        self.operation_repo.finish(op_id, record)

    def _on_scan_failed(self, message: str) -> None:
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(False)
        self.progress_label.setText("")
        QMessageBox.critical(self, "Echec de l'analyse", message)

    # --- Filtres et selection ---

    def _apply_filters(self) -> None:
        self.table.apply_filters(
            search=self.search_edit.text(),
            category=self.category_combo.currentData() or "",
            protection=self.protection_combo.currentData() or "",
            recommendation=self.reco_combo.currentData() or "",
            only_candidates=self.only_candidates_check.isChecked(),
        )
        self._update_summary()

    def _update_summary(self) -> None:
        if self.last_result is None:
            self.summary.setText("")
            return
        selected = len(self.table.selected_candidates())
        self.summary.setText(
            f"{self.last_result.analyzed} analyses | "
            f"{self.last_result.protected} proteges | "
            f"{self.last_result.candidate_count} candidats | "
            f"{selected} selectionnes"
        )

    # --- Nettoyage controle ---

    def _start_cleanup(self, mode: CleanupMode) -> None:
        if self.connection_service is None or not self.connection_service.is_connected:
            QMessageBox.warning(
                self, "Compte non connecte", "Connectez d'abord un compte Gmail."
            )
            return
        if self.last_result is None:
            QMessageBox.information(
                self, "Aucune analyse", "Lancez d'abord une analyse des e-mails."
            )
            return
        if self.cleanup_runner.is_running() or self.runner.is_running():
            return

        selected = self.table.selected_candidates()
        if not selected:
            QMessageBox.information(
                self, "Aucune selection", "Selectionnez au moins un message."
            )
            return

        dry_run = self.settings_repo.get_bool("dry_run", self.settings.dry_run)
        cutoff = self._cutoff()
        account = self.connection_service.account_email

        dialog = ConfirmationDialog(
            mode=mode,
            account=account,
            count=len(selected),
            protected_count=self.last_result.protected,
            cutoff=cutoff,
            dry_run=dry_run,
            parent=self,
        )
        if dialog.exec() != ConfirmationDialog.DialogCode.Accepted:
            return

        confirmation = Confirmation(
            mode=mode,
            confirmed_count=len(selected),
            account=account,
            cutoff=cutoff,
            phrase=dialog.phrase(),
            human_validated=True,
            dry_run=dry_run,
        )

        max_delete = self.settings_repo.get_int(
            "max_delete_per_run", self.settings.max_delete_per_run
        )
        tz = self._timezone()
        protected = self.contact_repo.emails()
        selected_copy = list(selected)

        self.scan_button.setEnabled(False)
        self.trash_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.progress.setVisible(True)
        self.progress_label.setText("Preparation du nettoyage...")

        def task(emit_progress):
            client = self.connection_service.client()
            service = CleanupService(
                client=client,
                protection=ProtectionService(protected_emails=protected),
                max_delete=max_delete,
                dry_run=dry_run,
                tz_name=tz,
                progress=emit_progress,
            )
            return service.execute(selected_copy, mode, confirmation, cutoff=cutoff)

        self.cleanup_runner.run(task)

    def _on_cleanup_finished(self, result: object) -> None:
        self._restore_action_buttons()
        if not isinstance(result, CleanupResult):
            self._on_cleanup_failed("Resultat de nettoyage inattendu.")
            return

        self._record_operation(result)

        verb = "supprime(s) definitivement" if result.mode == CleanupMode.DELETE else "mis en corbeille"
        lines = [
            f"Mode : {'SIMULATION' if result.dry_run else 'REEL'}",
            f"Messages {verb} : {result.deleted + result.trashed}",
            f"Messages ecartes : {result.skipped}",
            f"Echecs : {result.failed}",
        ]
        if result.dry_run:
            lines.append("\nAucune modification n'a ete effectuee sur Gmail (simulation).")
        if result.stopped_early:
            lines.append(
                "\nOperation arretee apres une erreur. Les messages deja supprimes "
                "ne peuvent pas etre restaures par l'application."
            )
        if result.details:
            lines.append("\nDetails :\n- " + "\n- ".join(result.details[:15]))
        QMessageBox.information(self, "Nettoyage termine", "\n".join(lines))

        if not result.dry_run and result.processed_ids:
            self._remove_processed(result.processed_ids)

    def _on_cleanup_failed(self, message: str) -> None:
        self._restore_action_buttons()
        QMessageBox.critical(self, "Echec du nettoyage", message)

    def _restore_action_buttons(self) -> None:
        self.scan_button.setEnabled(True)
        self.trash_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.progress.setVisible(False)
        self.progress_label.setText("")

    def _record_operation(self, result: CleanupResult) -> None:
        if self.operation_repo is None or self.last_result is None:
            return
        from src.database.repositories import OperationRecord

        record = OperationRecord(
            kind="nettoyage_" + result.mode.value,
            account=self.connection_service.account_email if self.connection_service else "",
            age_months=self._age_months(),
            analyzed=self.last_result.analyzed,
            excluded=self.last_result.excluded,
            protected=self.last_result.protected,
            candidates=self.last_result.candidate_count,
            selected=result.deleted + result.trashed + result.skipped,
            deleted=result.deleted,
            failed=result.failed,
            dry_run=result.dry_run,
            status="termine",
        )
        op_id = self.operation_repo.create(record)
        self.operation_repo.finish(op_id, record)

    def _remove_processed(self, processed_ids: list[str]) -> None:
        if self.last_result is None:
            return
        processed = set(processed_ids)
        self.last_result.candidates = [
            c for c in self.last_result.candidates if c.message.id not in processed
        ]
        self.table.set_candidates(self.last_result.candidates)
        self._apply_filters()
        self._update_summary()

    def _cutoff(self):
        tz = self._timezone()
        return compute_cutoff(datetime.now(get_zoneinfo(tz)), self._age_months(), tz)

    # --- Apercu ---

    def _preview_current_row(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Apercu", "Selectionnez d'abord un message.")
            return
        item = self.table.item(row, 0)
        candidate = item.data(Qt.ItemDataRole.UserRole) if item else None
        if candidate is not None:
            self._on_preview(candidate)

    def _on_preview(self, candidate: Candidate) -> None:
        body = "(corps indisponible)"
        if self.connection_service is not None and self.connection_service.is_connected:
            try:
                body = self.connection_service.client().get_message_body(candidate.message.id)
            except Exception as exc:
                body = f"(impossible de recuperer le corps : {exc})"
        dialog = PreviewDialog(candidate, body, self._timezone(), self)
        dialog.exec()
