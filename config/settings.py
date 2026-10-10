"""Configuration centrale de Lisht Mail Cleaner.

Charge les parametres depuis le fichier .env (s'il existe) et applique
des valeurs par defaut sures. Aucun secret n'est jamais ecrit en dur ici.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependance listee dans requirements.txt
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False

# Racine du projet = dossier contenant ce fichier remonte de deux niveaux.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "oui", "vrai"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def system_timezone() -> str:
    """Determine le fuseau horaire local de facon robuste.

    Cherche successivement : variable TZ, /etc/timezone, puis repli UTC.
    """
    tz = os.getenv("TZ")
    if tz:
        return tz
    etc = Path("/etc/timezone")
    if etc.is_file():
        try:
            value = etc.read_text(encoding="utf-8").strip()
            if value:
                return value
        except OSError:
            pass
    return "UTC"


@dataclass(frozen=True)
class Settings:
    """Parametres applicatifs immuables charges une fois au demarrage."""

    project_root: Path = PROJECT_ROOT
    timezone: str = field(default_factory=system_timezone)
    age_months: int = 2
    dry_run: bool = True
    max_delete_per_run: int = 50
    ollama_model: str = "qwen2.5:1.5b-instruct"
    ollama_host: str = "http://localhost:11434"
    log_level: str = "INFO"
    access_level: str = "corbeille"
    schedule_enabled: bool = False
    schedule_weekday: int = 6
    schedule_hour: int = 9
    schedule_minute: int = 0
    db_path: Path = PROJECT_ROOT / "data" / "lisht_mail_cleaner.db"
    credentials_path: Path = PROJECT_ROOT / "credentials" / "credentials.json"
    log_dir: Path = PROJECT_ROOT / "logs"

    def ensure_directories(self) -> None:
        """Cree les dossiers locaux necessaires au fonctionnement."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)


def load_settings(env_file: Path | None = None) -> Settings:
    """Charge la configuration depuis .env puis l'environnement."""
    env_path = env_file or (PROJECT_ROOT / ".env")
    if env_path.is_file():
        load_dotenv(env_path, override=False)

    def _path(name: str, default: Path) -> Path:
        raw = os.getenv(name)
        if not raw:
            return default
        candidate = Path(raw)
        return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate

    return Settings(
        timezone=os.getenv("LMC_TIMEZONE") or system_timezone(),
        age_months=_env_int("LMC_AGE_MONTHS", 2),
        dry_run=_env_bool("LMC_DRY_RUN", True),
        max_delete_per_run=_env_int("LMC_MAX_DELETE_PER_RUN", 50),
        ollama_model=os.getenv("LMC_OLLAMA_MODEL", "qwen2.5:1.5b-instruct"),
        ollama_host=os.getenv("LMC_OLLAMA_HOST", "http://localhost:11434"),
        log_level=os.getenv("LMC_LOG_LEVEL", "INFO").upper(),
        access_level=os.getenv("LMC_ACCESS_LEVEL", "corbeille").strip().lower(),
        schedule_enabled=_env_bool("LMC_SCHEDULE_ENABLED", False),
        schedule_weekday=_env_int("LMC_SCHEDULE_WEEKDAY", 6),
        schedule_hour=_env_int("LMC_SCHEDULE_HOUR", 9),
        schedule_minute=_env_int("LMC_SCHEDULE_MINUTE", 0),
        db_path=_path("LMC_DB_PATH", PROJECT_ROOT / "data" / "lisht_mail_cleaner.db"),
        credentials_path=_path(
            "LMC_CREDENTIALS_PATH", PROJECT_ROOT / "credentials" / "credentials.json"
        ),
        log_dir=_path("LMC_LOG_DIR", PROJECT_ROOT / "logs"),
    )


APP_NAME = "Lisht Mail Cleaner"
APP_VERSION = "0.1.0"
