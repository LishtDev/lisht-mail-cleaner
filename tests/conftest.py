"""Configuration pytest : rend le projet importable depuis les tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Force le rendu hors ecran pour les tests d'interface (CI/sans affichage).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
