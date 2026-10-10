"""Fenetre principale : navigation laterale et pages de l'application."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config.settings import APP_NAME, APP_VERSION
from src.ui.analysis_view import AnalysisView
from src.ui.dashboard import DashboardView
from src.ui.history_view import HistoryView
from src.ui.report_view import ReportView
from src.ui.settings_view import SettingsView
from src.services.scheduler_service import SchedulerService


class MainWindow(QWidget):
    """Fenetre racine contenant la barre laterale et les pages."""

    def __init__(
        self,
        settings,
        settings_repo,
        connection_service=None,
        local_model=None,
        contact_repo=None,
        operation_repo=None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.settings_repo = settings_repo
        self.connection_service = connection_service
        self.local_model = local_model
        self.contact_repo = contact_repo
        self.operation_repo = operation_repo
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1080, 720)
        self._build()

    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        self.dashboard = DashboardView(
            self.settings, self.connection_service, self.local_model
        )
        self.settings_view = SettingsView(
            self.settings,
            self.settings_repo,
            self.contact_repo,
            connection_service=self.connection_service,
        )
        self.settings_view.access_level_changed.connect(self._on_access_level_changed)
        self.scheduler = SchedulerService(tz_name=self.settings.timezone)
        self.scheduler.scan_requested.connect(self.run_scheduled_scan)
        self.settings_view.scheduler = self.scheduler
        self._restore_schedule()
        self.settings_view._load_schedule()
        self.analysis_view = AnalysisView(
            self.settings,
            self.settings_repo,
            self.contact_repo,
            self.connection_service,
            self.local_model,
            self.operation_repo,
        )
        self.pages.addWidget(self.dashboard)
        self.pages.addWidget(self.analysis_view)
        self.pages.addWidget(self.settings_view)
        self.history_view = HistoryView(
            lambda: self.settings, self.operation_repo, self.settings.timezone
        )
        self.report_view = ReportView(
            self.settings,
            lambda: self.analysis_view.last_result,
            self.connection_service,
            self.settings.timezone,
        )
        self.pages.addWidget(self.history_view)
        self.pages.addWidget(self.report_view)
        root.addWidget(self.pages, stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(4)

        title = QLabel(APP_NAME)
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        labels = [
            "Tableau de bord",
            "Analyse des e-mails",
            "Parametres",
            "Historique",
            "Rapport",
        ]
        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setObjectName("sidebarButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if index == 0:
                button.setChecked(True)
            self.nav_group.addButton(button, index)
            layout.addWidget(button)

        self.nav_group.idClicked.connect(self._on_nav_clicked)

        layout.addStretch(1)

        footer = QLabel(f"Version {APP_VERSION}\nTraitement IA local")
        footer.setObjectName("pageSubtitle")
        footer.setWordWrap(True)
        layout.addWidget(footer)

        return sidebar

    def _on_nav_clicked(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        if index == 1 and hasattr(self, "analysis_view"):
            self.analysis_view._refresh_subtitle()
        elif index == 3 and hasattr(self, "history_view"):
            self.history_view.refresh()
        elif index == 4 and hasattr(self, "report_view"):
            self.report_view.refresh()

    def _restore_schedule(self) -> None:
        """Active le scan hebdomadaire si l'utilisateur l'avait configure."""
        self.scheduler.configure(
            self.settings_repo.get_int("schedule_weekday", self.settings.schedule_weekday),
            self.settings_repo.get_int("schedule_hour", self.settings.schedule_hour),
            self.settings_repo.get_int("schedule_minute", self.settings.schedule_minute),
        )
        if self.settings_repo.get_bool("schedule_enabled", self.settings.schedule_enabled):
            self.scheduler.start()

    def run_scheduled_scan(self) -> None:
        """Slot appele par le planificateur : scan en lecture seule uniquement."""
        self.pages.setCurrentIndex(1)
        if hasattr(self, "analysis_view"):
            self.analysis_view.start_scheduled_scan()

    def _on_access_level_changed(self) -> None:
        """Met a jour l'affichage de connexion apres un changement de droit."""
        if hasattr(self, "dashboard"):
            self.dashboard._sync_connection_display()

    def closeEvent(self, event) -> None:
        """Ferme proprement les taches d'arriere-plan avant de quitter."""
        if hasattr(self, "analysis_view"):
            self.analysis_view.stop_background()
        if hasattr(self, "dashboard"):
            self.dashboard.stop_background()
        if hasattr(self, "scheduler"):
            self.scheduler.stop()
        event.accept()
