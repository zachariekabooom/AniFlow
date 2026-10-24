"""IA locale exclusive (Ollama). Aucun fournisseur cloud, aucun repli distant."""

from .errors import (
    AICapabilityError,
    AIError,
    AIModelMissingError,
    AINotLocalError,
    AIResponseError,
    AIUnavailableError,
)
from .ollama_client import AIStatus, ChatResult, ModelEntry, ModelInfo, OllamaClient

__all__ = [
    "AICapabilityError",
    "AIError",
    "AIModelMissingError",
    "AINotLocalError",
    "AIResponseError",
    "AIStatus",
    "AIUnavailableError",
    "ChatResult",
    "ModelEntry",
    "ModelInfo",
    "OllamaClient",
]
