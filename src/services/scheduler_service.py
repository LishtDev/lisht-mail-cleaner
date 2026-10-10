"""Planification d'un scan hebdomadaire (section 13).

Le planificateur integre (APScheduler) declenche UNIQUEMENT un scan en
lecture seule. Il ne supprime JAMAIS de message : toute suppression exige
une confirmation humaine explicite ulterieure.

La fonction `compute_next_run` est pure et testable (changement d'heure,
passage de semaine, fuseaux horaires).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QObject, Signal

from src.utils.dates import get_zoneinfo
from src.utils.logging_config import get_logger

logger = get_logger("services.scheduler")

# Jour de la semaine : 0 = lundi ... 6 = dimanche (comme Python).
WEEKDAY_NAMES = [
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
]


def compute_next_run(
    now: datetime, weekday: int, hour: int, minute: int = 0, tz_name: str = "UTC"
) -> datetime:
    """Calcule la prochaine occurrence hebdomadaire (pure, sans APScheduler)."""
    zone = get_zoneinfo(tz_name)
    reference = now.astimezone(zone)
    days_ahead = (weekday - reference.weekday()) % 7
    candidate = reference.replace(
        hour=hour, minute=minute, second=0, microsecond=0
    ) + timedelta(days=days_ahead)
    if candidate <= reference:
        candidate += timedelta(days=7)
    return candidate


class SchedulerService(QObject):
    """Enveloppe autour d'APScheduler pour un scan hebdomadaire en lecture seule."""

    scan_requested = Signal()

    def __init__(self, callback=None, tz_name: str = "UTC") -> None:
        super().__init__()
        self.callback = callback
        self.tz_name = tz_name
        self._scheduler = None
        self._weekday = 6
        self._hour = 9
        self._minute = 0

    @property
    def weekday(self) -> int:
        return self._weekday

    @property
    def hour(self) -> int:
        return self._hour

    @property
    def minute(self) -> int:
        return self._minute

    def configure(self, weekday: int, hour: int, minute: int = 0) -> None:
        """Definit le jour et l'heure du scan hebdomadaire."""
        if not 0 <= weekday <= 6:
            raise ValueError("Le jour doit etre compris entre 0 (lundi) et 6 (dimanche).")
        if not 0 <= hour <= 23:
            raise ValueError("L'heure doit etre comprise entre 0 et 23.")
        if not 0 <= minute <= 59:
            raise ValueError("Les minutes doivent etre comprises entre 0 et 59.")
        self._weekday = weekday
        self._hour = hour
        self._minute = minute

    def start(self) -> None:
        """Demarre le planificateur en arriere-plan."""
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        if self._scheduler is not None:
            return
        self._scheduler = BackgroundScheduler(timezone=get_zoneinfo(self.tz_name))
        trigger = CronTrigger(
            day_of_week=self._weekday,
            hour=self._hour,
            minute=self._minute,
            timezone=get_zoneinfo(self.tz_name),
        )
        self._scheduler.add_job(self._run_job, trigger=trigger, id="weekly_scan")
        self._scheduler.start()
        logger.info(
            "Planification activee : %s a %02d:%02d (%s)",
            WEEKDAY_NAMES[self._weekday],
            self._hour,
            self._minute,
            self.tz_name,
        )

    def _run_job(self) -> None:
        """Executée par APScheduler : signale un scan a l'interface (lecture seule)."""
        try:
            logger.info("Declenchement du scan hebdomadaire planifie")
            self.scan_requested.emit()
            if self.callback is not None:
                self.callback()
        except Exception as exc:  # pragma: no cover - depend de l'environnement
            logger.error("Echec du scan planifie : %s", exc)

    def stop(self) -> None:
        """Arrete le planificateur."""
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            logger.info("Planification arretee")

    def is_running(self) -> bool:
        return self._scheduler is not None

    def next_run(self, now: datetime | None = None) -> datetime | None:
        """Retourne la prochaine execution prevue."""
        if self._scheduler is not None:
            job = self._scheduler.get_job("weekly_scan")
            if job is not None and job.next_run_time is not None:
                return job.next_run_time
        reference = now or datetime.now(get_zoneinfo(self.tz_name))
        return compute_next_run(
            reference, self._weekday, self._hour, self._minute, self.tz_name
        )
