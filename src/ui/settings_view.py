"""Vue Parametres : generalites et contacts proteges (section 10)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.services.scheduler_service import WEEKDAY_NAMES
from src.ui.contacts_panel import ContactsPanel
from src.utils.dates import AGE_OPTIONS_MONTHS


class SettingsView(QWidget):
    """Configuration locale, persistee dans SQLite."""

    access_level_changed = Signal()

    def __init__(
        self,
        settings,
        settings_repo,
        contact_repo=None,
        scheduler=None,
        connection_service=None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.repo = settings_repo
        self.contact_repo = contact_repo
        self.scheduler = scheduler
        self.connection_service = connection_service
        self._build()
        self.load()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Parametres")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_schedule_tab(), "Planification")
        if self.contact_repo is not None:
            self.contacts_panel = ContactsPanel(self.contact_repo)
            tabs.addTab(self.contacts_panel, "Contacts proteges")
        layout.addWidget(tabs, stretch=1)

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        subtitle = QLabel(
            "Ces reglages sont enregistres localement dans la base SQLite du projet."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)

        self.age_combo = QComboBox()
        for months in AGE_OPTIONS_MONTHS:
            self.age_combo.addItem(f"{months} mois", months)
        form.addRow("Seuil d'anciennete", self.age_combo)

        self.access_combo = QComboBox()
        self.access_combo.addItem("Lecture seule (analyser uniquement)", "lecture")
        self.access_combo.addItem("Corbeille (recommande, reversible)", "corbeille")
        self.access_combo.addItem(
            "Complet (suppression definitive, irreversible)", "complet"
        )
        form.addRow("Niveau d'acces Gmail", self.access_combo)

        self.dry_run_check = QCheckBox("Activer le mode simulation (aucune suppression reelle)")
        form.addRow("Simulation", self.dry_run_check)

        self.max_delete_spin = QSpinBox()
        self.max_delete_spin.setRange(1, 10000)
        self.max_delete_spin.setValue(self.settings.max_delete_per_run)
        form.addRow("Limite de suppression par operation", self.max_delete_spin)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("qwen2.5:1.5b-instruct")
        form.addRow("Modele IA local (Ollama)", self.model_edit)

        self.tz_edit = QLineEdit()
        form.addRow("Fuseau horaire", self.tz_edit)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        form.addRow("Niveau de journalisation", self.log_level_combo)

        layout.addLayout(form)

        note = QLabel(
            "Pour toute suppression definitive, une autorisation de modification large est "
            "demandee par Gmail (perimetre complet). Voir docs/SECURITY.md."
        )
        note.setObjectName("pageSubtitle")
        note.setWordWrap(True)
        layout.addWidget(note)

        save_button = QPushButton("Enregistrer les parametres")
        save_button.setObjectName("primary")
        save_button.clicked.connect(self.save)
        layout.addWidget(save_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return tab

    def _build_schedule_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        subtitle = QLabel(
            "Un scan hebdomadaire peut analyser vos e-mails automatiquement. "
            "Il fonctionne UNIQUEMENT en lecture seule : aucune suppression "
            "automatique n'est jamais effectuee. Vous validez toujours chaque "
            "suppression manuellement."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)

        self.schedule_check = QCheckBox("Activer le scan hebdomadaire planifie")
        form.addRow("Planification", self.schedule_check)

        self.weekday_combo = QComboBox()
        for index, name in enumerate(WEEKDAY_NAMES):
            self.weekday_combo.addItem(name, index)
        form.addRow("Jour", self.weekday_combo)

        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setSuffix(" h")
        form.addRow("Heure", self.hour_spin)

        self.minute_spin = QSpinBox()
        self.minute_spin.setRange(0, 59)
        self.minute_spin.setSuffix(" min")
        form.addRow("Minutes", self.minute_spin)

        layout.addLayout(form)

        self.next_run_label = QLabel("")
        self.next_run_label.setObjectName("pageSubtitle")
        self.next_run_label.setWordWrap(True)
        layout.addWidget(self.next_run_label)

        save_button = QPushButton("Enregistrer la planification")
        save_button.setObjectName("primary")
        save_button.clicked.connect(self.save)
        layout.addWidget(save_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return tab

    def load(self) -> None:
        age = self.repo.get_int("age_months", self.settings.age_months)
        index = self.age_combo.findData(age)
        if index >= 0:
            self.age_combo.setCurrentIndex(index)
        level = self.repo.get("access_level", self.settings.access_level) or "corbeille"
        access_index = self.access_combo.findData(level)
        if access_index >= 0:
            self.access_combo.setCurrentIndex(access_index)
        self.dry_run_check.setChecked(self.repo.get_bool("dry_run", self.settings.dry_run))
        self.max_delete_spin.setValue(
            self.repo.get_int("max_delete_per_run", self.settings.max_delete_per_run)
        )
        self.model_edit.setText(self.repo.get("ollama_model", self.settings.ollama_model) or "")
        self.tz_edit.setText(self.repo.get("timezone", self.settings.timezone) or "")
        level = self.repo.get("log_level", self.settings.log_level) or "INFO"
        level_index = self.log_level_combo.findText(level.upper())
        if level_index >= 0:
            self.log_level_combo.setCurrentIndex(level_index)
        self._load_schedule()

    def _load_schedule(self) -> None:
        enabled = self.repo.get_bool("schedule_enabled", self.settings.schedule_enabled)
        self.schedule_check.setChecked(enabled)
        weekday = self.repo.get_int("schedule_weekday", self.settings.schedule_weekday)
        index = self.weekday_combo.findData(weekday)
        if index >= 0:
            self.weekday_combo.setCurrentIndex(index)
        self.hour_spin.setValue(
            self.repo.get_int("schedule_hour", self.settings.schedule_hour)
        )
        self.minute_spin.setValue(
            self.repo.get_int("schedule_minute", self.settings.schedule_minute)
        )
        self._update_next_run_label()

    def _update_next_run_label(self) -> None:
        if self.scheduler is None:
            self.next_run_label.setText("")
            return
        if not self.schedule_check.isChecked():
            self.next_run_label.setText("Planification desactivee.")
            return
        weekday = self.weekday_combo.currentData()
        self.scheduler.configure(
            weekday, self.hour_spin.value(), self.minute_spin.value()
        )
        nxt = self.scheduler.next_run()
        if nxt is not None:
            self.next_run_label.setText(
                f"Prochaine analyse planifiee : {nxt.strftime('%Y-%m-%d %H:%M')}."
            )

    def save(self) -> None:
        previous_level = self.repo.get("access_level", self.settings.access_level)
        new_level = self.access_combo.currentData()
        self.repo.set("age_months", str(self.age_combo.currentData()))
        self.repo.set("dry_run", "true" if self.dry_run_check.isChecked() else "false")
        self.repo.set("max_delete_per_run", str(self.max_delete_spin.value()))
        self.repo.set("ollama_model", self.model_edit.text().strip())
        self.repo.set("timezone", self.tz_edit.text().strip())
        self.repo.set("log_level", self.log_level_combo.currentText())
        self.repo.set("access_level", new_level)
        self._save_schedule()
        self._apply_access_level(previous_level, new_level)
        QMessageBox.information(
            self, "Parametres enregistres", "Les parametres ont ete enregistres localement."
        )

    def _apply_access_level(self, previous_level: str, new_level: str) -> None:
        if previous_level == new_level or self.connection_service is None:
            return
        was_connected = self.connection_service.is_connected
        self.connection_service.set_access_level(new_level)
        self.access_level_changed.emit()
        if was_connected:
            QMessageBox.warning(
                self,
                "Reconnexion necessaire",
                "Le niveau d'acces Gmail a change. Vous avez ete deconnecte : "
                "reconnectez-vous depuis le tableau de bord pour accorder le "
                "nouveau droit.",
            )

    def _save_schedule(self) -> None:
        enabled = self.schedule_check.isChecked()
        weekday = self.weekday_combo.currentData()
        hour = self.hour_spin.value()
        minute = self.minute_spin.value()
        self.repo.set("schedule_enabled", "true" if enabled else "false")
        self.repo.set("schedule_weekday", str(weekday))
        self.repo.set("schedule_hour", str(hour))
        self.repo.set("schedule_minute", str(minute))
        if self.scheduler is not None:
            self.scheduler.configure(weekday, hour, minute)
            if enabled:
                self.scheduler.start()
            else:
                self.scheduler.stop()
        self._update_next_run_label()
