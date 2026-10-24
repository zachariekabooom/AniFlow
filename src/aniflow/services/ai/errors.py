"""Erreurs de la couche IA locale, avec messages français et étapes de dépannage."""

from __future__ import annotations


class AIError(Exception):
    default_user_message = "La fonction IA a rencontré une erreur. Aucun service distant n'a été utilisé."

    def __init__(self, message: str | None = None, *, user_message: str | None = None) -> None:
        super().__init__(message or user_message or self.default_user_message)
        self.user_message = user_message or self.default_user_message


class AINotLocalError(AIError):
    """Adresse non locale, modèle cloud ou redirection : refusé sans aucun appel sortant."""


class AIUnavailableError(AIError):
    def __init__(self, message: str | None = None, *, url: str = "") -> None:
        where = f" sur {url}" if url else ""
        super().__init__(
            message,
            user_message=(
                f"Ollama ne répond pas{where}. Vérifiez qu'Ollama est lancé (icône dans la zone de notification "
                "de Windows) ou démarrez-le avec « ollama serve », puis réessayez. Aucune bascule vers un service distant."
            ),
        )


class AIModelMissingError(AIError):
    def __init__(self, model: str) -> None:
        super().__init__(
            f"modèle absent : {model}",
            user_message=(
                f"Le modèle « {model} » n'est pas installé dans Ollama. Installez-le vous-même avec "
                f"« ollama pull {model} » ; AniFlow ne télécharge jamais de modèle sans votre accord."
            ),
        )
        self.model = model


class AICapabilityError(AIError):
    """Le modèle (ou ce client) ne prend pas en charge la modalité demandée."""


class AIResponseError(AIError):
    def __init__(self, message: str, *, detail: str | None = None) -> None:
        extra = f" Détail d'Ollama : {detail}" if detail else ""
        super().__init__(
            message,
            user_message=f"Ollama a renvoyé une réponse inutilisable.{extra} Si le message évoque la mémoire, essayez un modèle plus léger.",
        )
        self.detail = detail
