"""Execution d'une tache en arriere-plan pour ne pas figer l'interface.

Utilise pour l'authentification OAuth (qui attend une action du navigateur)
et, plus tard, pour les scans longs.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal


class Worker(QObject):
    """Execute une fonction dans un thread et signale le resultat."""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, function: Callable, *args, **kwargs) -> None:
        super().__init__()
        self._function = function
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._function(*self._args, **self._kwargs)
        except Exception as exc:  # message comprehensible pour l'utilisateur
            self.failed.emit(str(exc))
        else:
            self.finished.emit(result)


class TaskRunner(QObject):
    """Lance un Worker dans un QThread et nettoie a la fin."""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: Worker | None = None

    def run(self, function: Callable, *args, **kwargs) -> None:
        if self._thread is not None:
            raise RuntimeError("Une tache est deja en cours.")

        self._thread = QThread()
        self._worker = Worker(function, *args, **kwargs)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()

    def _on_finished(self, result: object) -> None:
        self.finished.emit(result)

    def _on_failed(self, message: str) -> None:
        self.failed.emit(message)

    def _cleanup(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def wait(self, ms: int = 3000) -> bool:
        """Demande l'arret du thread et attend sa fin (avec delai maximal)."""
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            return self._thread.wait(ms)
        return True


class ProgressWorker(QObject):
    """Execute une tache qui remonte sa progression.

    La tache est un appelable recevant un callback `emit_progress(int, str)`
    et retournant un resultat.
    """

    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(self, task: Callable) -> None:
        super().__init__()
        self._task = task

    def run(self) -> None:
        try:
            result = self._task(self.progress.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished.emit(result)


class ProgressTaskRunner(QObject):
    """Lance un ProgressWorker dans un QThread, avec signaux de progression."""

    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: ProgressWorker | None = None

    def run(self, task: Callable) -> None:
        if self.is_running():
            raise RuntimeError("Une tache est deja en cours.")
        self._thread = QThread()
        self._worker = ProgressWorker(task)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress)
        self._worker.finished.connect(self.finished)
        self._worker.failed.connect(self.failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()

    def _cleanup(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def wait(self, ms: int = 3000) -> bool:
        """Demande l'arret du thread et attend sa fin (avec delai maximal)."""
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            return self._thread.wait(ms)
        return True
