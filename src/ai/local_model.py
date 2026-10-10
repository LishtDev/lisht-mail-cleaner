"""Acces au moteur IA local (Ollama).

Le contenu des e-mails n'est jamais transmis a un service distant : tout
le traitement se fait via le serveur Ollama local.

Avant toute analyse, on verifie que le moteur repond et que le modele
requis est disponible (section 8).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.utils.logging_config import get_logger

logger = get_logger("ai.local_model")


@dataclass(frozen=True)
class ModelStatus:
    """Etat du moteur IA local et du modele demande."""

    engine_available: bool = False
    model_present: bool = False
    model_name: str = ""
    error: str = ""

    @property
    def ready(self) -> bool:
        return self.engine_available and self.model_present


class LocalModel:
    """Client minimal pour Ollama."""

    def __init__(self, model_name: str, host: str = "http://localhost:11434") -> None:
        self.model_name = model_name
        self.host = host

    def _client(self):
        import ollama

        return ollama.Client(host=self.host)

    def check_status(self) -> ModelStatus:
        """Verifie l'acces au moteur et la presence du modele."""
        try:
            client = self._client()
            response = client.list()
        except Exception as exc:
            logger.info("Moteur Ollama indisponible : %s", exc)
            return ModelStatus(
                engine_available=False,
                model_present=False,
                model_name=self.model_name,
                error=f"Moteur Ollama non accessible ({exc}).",
            )

        names = _extract_model_names(response)
        present = any(
            name == self.model_name or name.startswith(self.model_name + ":")
            for name in names
        )
        if not present:
            return ModelStatus(
                engine_available=True,
                model_present=False,
                model_name=self.model_name,
                error=(
                    f"Modele « {self.model_name} » absent. "
                    f"Installez-le avec : ollama pull {self.model_name}"
                ),
            )
        return ModelStatus(
            engine_available=True,
            model_present=True,
            model_name=self.model_name,
        )

    def generate_json(self, prompt: str, system: str, timeout: float = 60.0) -> str:
        """Envoie un message au modele en demandant une reponse JSON.

        Leve RuntimeError si le moteur ne repond pas.
        """
        try:
            client = self._client()
            response = client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                format="json",
                options={"temperature": 0.0, "num_predict": 256},
            )
        except Exception as exc:
            raise RuntimeError(f"Erreur du moteur IA local : {exc}") from exc

        if isinstance(response, dict):
            message = response.get("message", {})
            return message.get("content", "") or ""
        return getattr(getattr(response, "message", None), "content", "") or ""


def _extract_model_names(response) -> list[str]:
    """Extrait la liste des noms de modeles depuis une reponse ollama.list()."""
    models = []
    if isinstance(response, dict):
        items = response.get("models", [])
    else:
        items = getattr(response, "models", []) or []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name") or item.get("model", "")
        else:
            name = getattr(item, "name", "") or getattr(item, "model", "")
        if name:
            models.append(name)
    return models
