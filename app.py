#!/usr/bin/env python3
"""Lisht Mail Cleaner - point d'entree de l'application de bureau.

Lance l'interface PySide6 apres avoir charge la configuration, initialise
la journalisation et prepare la base locale. Aucune operation destructive
n'est effectuee au demarrage.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from config.settings import APP_NAME, load_settings
from src.ai.local_model import LocalModel
from src.database.database import Database
from src.database.repositories import (
    OperationRepository,
    ProtectedContactRepository,
    SettingsRepository,
)
from src.services.connection_service import ConnectionService
from src.ui.main_window import MainWindow
from src.ui.theme import STYLESHEET
from src.utils.logging_config import configure_logging, get_logger


def main() -> int:
    """Point d'entree principal."""
    settings = load_settings()
    settings.ensure_directories()
    configure_logging(settings.log_dir, settings.log_level)
    logger = get_logger("app")
    logger.info("Demarrage de %s", APP_NAME)

    database = Database(settings.db_path)
    try:
        database.initialize()
        database.secure_permissions()
    except Exception as exc:  # pragma: no cover - depend de l'environnement
        logger.error("Base SQLite inaccessible : %s", exc)
        print(f"Erreur : base SQLite inaccessible ({exc}).", file=sys.stderr)
        return 1

    settings_repo = SettingsRepository(database)
    contact_repo = ProtectedContactRepository(database)
    operation_repo = OperationRepository(database)

    access_level = settings_repo.get("access_level", settings.access_level) or settings.access_level

    connection_service = ConnectionService.create(
        credentials_path=settings.credentials_path,
        fallback_dir=settings.project_root / "data",
        tz_name=settings.timezone,
        access_level=access_level,
    )

    local_model = LocalModel(settings.ollama_model, settings.ollama_host)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(STYLESHEET)

    window = MainWindow(
        settings,
        settings_repo,
        connection_service,
        local_model,
        contact_repo,
        operation_repo,
    )
    window.show()

    logger.info("Interface affichee")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
