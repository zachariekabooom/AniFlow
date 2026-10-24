"""Client Ollama strictement local : unique point d'entrée de l'IA dans AniFlow.

Garanties (SPEC §9 et critère 12) :
- l'adresse doit être une adresse de bouclage (127.0.0.0/8, ::1, localhost) ;
- les modèles « cloud » d'Ollama (suffixe -cloud, ou entrée /api/tags avec remote_host/remote_model)
  sont refusés avant tout appel, car ils s'exécuteraient sur les serveurs d'Ollama ;
- aucune redirection suivie, aucun proxy système, aucun repli distant ;
- aucune modalité n'est envoyée à un modèle dont /api/show ne l'annonce pas (échec fermé si inconnu) ;
- aucun téléchargement de modèle (jamais d'appel à /api/pull).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from aniflow import __version__
from aniflow.net.local_only import (
    DEFAULT_OLLAMA_URL,
    NotLocalError,
    ensure_not_cloud_name,
    has_remote_markers,
    validate_local_base_url,
)
from aniflow.net.transport import HttpTransport, TransportError, UrllibTransport

from .errors import (
    AICapabilityError,
    AIModelMissingError,
    AINotLocalError,
    AIResponseError,
    AIUnavailableError,
)

CAP_VISION = "vision"
CAP_AUDIO = "audio"
CAP_THINKING = "thinking"

_ALLOWED_MESSAGE_KEYS = {"role", "content", "images", "thinking", "tool_calls", "tool_name"}
_ALLOWED_ROLES = {"system", "user", "assistant", "tool"}

STATE_READY = "ready"
STATE_UNAVAILABLE = "unavailable"
STATE_NO_MODEL = "no_model_configured"
STATE_MODEL_MISSING = "model_missing"
STATE_NOT_LOCAL = "not_local"


def _opt_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


@dataclass(frozen=True)
class ModelEntry:
    name: str
    size_bytes: int | None
    digest: str | None
    family: str | None
    parameter_size: str | None
    quantization: str | None
    is_remote: bool


@dataclass(frozen=True)
class ModelInfo:
    name: str
    capabilities: frozenset[str] | None  # None : Ollama n'annonce pas de capacités (version trop ancienne ?)
    family: str | None
    parameter_size: str | None
    quantization: str | None
    context_length: int | None

    def supports(self, capability: str) -> bool | None:
        """True/False si les capacités sont connues, None sinon (à traiter comme « non »)."""
        return None if self.capabilities is None else capability in self.capabilities


@dataclass(frozen=True)
class RunningModel:
    name: str
    size_bytes: int | None
    size_vram_bytes: int | None


@dataclass(frozen=True)
class ChatMetrics:
    total_seconds: float | None
    load_seconds: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    tokens_per_second: float | None


@dataclass(frozen=True)
class ChatResult:
    data: Any  # JSON décodé de la réponse du modèle (une proposition, jamais un fait garanti)
    raw_text: str
    model: str
    metrics: ChatMetrics


@dataclass(frozen=True)
class AIStatus:
    state: str
    ok: bool
    message: str  # français, affichable tel quel
    version: str | None = None
    model: str | None = None
    capabilities: tuple[str, ...] = ()


def _ns_to_s(value: Any) -> float | None:
    number = _opt_int(value)
    return None if number is None else number / 1e9


def _metrics(data: Mapping[str, Any]) -> ChatMetrics:
    eval_count = _opt_int(data.get("eval_count"))
    eval_ns = _opt_int(data.get("eval_duration"))
    speed = (eval_count / (eval_ns / 1e9)) if eval_count and eval_ns else None
    return ChatMetrics(
        total_seconds=_ns_to_s(data.get("total_duration")),
        load_seconds=_ns_to_s(data.get("load_duration")),
        prompt_tokens=_opt_int(data.get("prompt_eval_count")),
        completion_tokens=eval_count,
        tokens_per_second=speed,
    )


class OllamaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        *,
        transport: HttpTransport | None = None,
        timeout: float = 5.0,
        chat_timeout: float = 300.0,
        verify_ttl: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        try:
            self.base_url = validate_local_base_url(base_url)
        except NotLocalError as exc:
            raise AINotLocalError(str(exc), user_message=exc.user_message) from exc
        self._transport = transport or UrllibTransport(use_system_proxy=False)
        self._timeout = timeout
        self._chat_timeout = chat_timeout
        self._verify_ttl = verify_ttl
        self._clock = clock
        self._verified: dict[str, tuple[float, ModelInfo]] = {}

    # ----- Diagnostic -----

    def version(self) -> str:
        data = self._request_json("GET", "/api/version")
        version = data.get("version")
        if not isinstance(version, str):
            raise AIResponseError("réponse /api/version sans numéro de version")
        return version

    def list_models(self) -> list[ModelEntry]:
        data = self._request_json("GET", "/api/tags")
        entries: list[ModelEntry] = []
        for raw in data.get("models") or []:
            if not isinstance(raw, Mapping) or not isinstance(raw.get("name"), str):
                continue
            details = raw.get("details") if isinstance(raw.get("details"), Mapping) else {}
            entries.append(
                ModelEntry(
                    name=raw["name"],
                    size_bytes=_opt_int(raw.get("size")),
                    digest=raw.get("digest") if isinstance(raw.get("digest"), str) else None,
                    family=details.get("family") if isinstance(details.get("family"), str) else None,
                    parameter_size=details.get("parameter_size") if isinstance(details.get("parameter_size"), str) else None,
                    quantization=details.get("quantization_level") if isinstance(details.get("quantization_level"), str) else None,
                    is_remote=has_remote_markers(raw) or _is_cloud(raw["name"]),
                )
            )
        return entries

    def running(self) -> list[RunningModel]:
        data = self._request_json("GET", "/api/ps")
        return [
            RunningModel(raw["name"], _opt_int(raw.get("size")), _opt_int(raw.get("size_vram")))
            for raw in data.get("models") or []
            if isinstance(raw, Mapping) and isinstance(raw.get("name"), str)
        ]

    def check_ready(self, model: str | None) -> AIStatus:
        """État de la fonction IA, sans jamais lever : prêt à afficher dans les Paramètres."""
        if model:
            try:
                ensure_not_cloud_name(model)  # refus avant tout appel, même vers le serveur local
            except NotLocalError as exc:
                return AIStatus(STATE_NOT_LOCAL, False, exc.user_message, model=model)
        try:
            version = self.version()
            if not model:
                return AIStatus(STATE_NO_MODEL, False, "Aucun modèle IA n'est choisi. Sélectionnez un modèle installé dans Paramètres > IA locale.", version)
            info = self.ensure_usable(model)
        except AIUnavailableError as exc:
            return AIStatus(STATE_UNAVAILABLE, False, exc.user_message)
        except AIModelMissingError as exc:
            return AIStatus(STATE_MODEL_MISSING, False, exc.user_message, model=model)
        except AINotLocalError as exc:
            return AIStatus(STATE_NOT_LOCAL, False, exc.user_message, model=model)
        except AIResponseError as exc:
            return AIStatus(STATE_UNAVAILABLE, False, exc.user_message, model=model)
        caps = tuple(sorted(info.capabilities or ()))
        return AIStatus(STATE_READY, True, "Modèle local prêt.", version, model, caps)

    # ----- Modèles -----

    def show(self, model: str) -> ModelInfo:
        try:
            ensure_not_cloud_name(model)
        except NotLocalError as exc:
            raise AINotLocalError(str(exc), user_message=exc.user_message) from exc
        data = self._request_json("POST", "/api/show", {"model": model}, model=model)
        if has_remote_markers(data):
            raise AINotLocalError(
                f"modèle distant refusé : {model}",
                user_message=f"Le modèle « {model} » est exécuté à distance par Ollama. Choisissez un modèle installé localement.",
            )
        raw_caps = data.get("capabilities")
        caps = frozenset(str(c).lower() for c in raw_caps) if isinstance(raw_caps, list) else None
        details = data.get("details") if isinstance(data.get("details"), Mapping) else {}
        context = None
        for key, value in (data.get("model_info") or {}).items() if isinstance(data.get("model_info"), Mapping) else ():
            if str(key).endswith(".context_length"):
                context = _opt_int(value)
        return ModelInfo(
            name=model,
            capabilities=caps,
            family=details.get("family") if isinstance(details.get("family"), str) else None,
            parameter_size=details.get("parameter_size") if isinstance(details.get("parameter_size"), str) else None,
            quantization=details.get("quantization_level") if isinstance(details.get("quantization_level"), str) else None,
            context_length=context,
        )

    def ensure_usable(self, model: str) -> ModelInfo:
        """Vérifie (avec un cache court) que le modèle est installé, local et décrit."""
        cached = self._verified.get(model)
        if cached and self._clock() - cached[0] < self._verify_ttl:
            return cached[1]
        info = self.show(model)
        self._verified[model] = (self._clock(), info)
        return info

    def require_capability(self, model: str, capability: str) -> ModelInfo:
        info = self.ensure_usable(model)
        if info.capabilities is None:
            raise AICapabilityError(
                f"capacités inconnues pour {model}",
                user_message=f"Ollama n'indique pas les capacités du modèle « {model} » (version trop ancienne ?). "
                f"Mettez Ollama à jour avant d'utiliser « {capability} ».",
            )
        if capability not in info.capabilities:
            raise AICapabilityError(
                f"{model} ne prend pas en charge {capability}",
                user_message=f"Le modèle « {model} » ne prend pas en charge « {capability} » dans cette installation d'Ollama. "
                "Choisissez un autre modèle ou prétraitez le média localement.",
            )
        return info

    # ----- Génération -----

    def chat_json(
        self,
        model: str,
        messages: Sequence[Mapping[str, Any]],
        *,
        schema: Mapping[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
        think: bool | None = None,
        keep_alive: str | int | None = None,
    ) -> ChatResult:
        """Demande une réponse JSON structurée. Le résultat est une proposition à valider par l'appelant."""
        info = self.ensure_usable(model)
        self._check_messages(model, info, messages)
        payload: dict[str, Any] = {
            "model": model,
            "messages": [dict(m) for m in messages],
            "stream": False,
            "format": dict(schema) if schema is not None else "json",
        }
        if options:
            payload["options"] = dict(options)
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
        if think is not None and info.supports(CAP_THINKING):
            payload["think"] = bool(think)
        data = self._request_json("POST", "/api/chat", payload, timeout=self._chat_timeout, model=model)
        message = data.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, str) or not content.strip():
            raise AIResponseError("réponse vide du modèle")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIResponseError("le modèle n'a pas renvoyé un JSON valide", detail=content[:200]) from exc
        return ChatResult(parsed, content, str(data.get("model") or model), _metrics(data))

    def _check_messages(self, model: str, info: ModelInfo, messages: Sequence[Mapping[str, Any]]) -> None:
        if not messages:
            raise ValueError("au moins un message est requis")
        for message in messages:
            if message.get("role") not in _ALLOWED_ROLES or not isinstance(message.get("content", ""), str):
                raise ValueError("message invalide : rôle ou contenu incorrect")
            unknown = set(message) - _ALLOWED_MESSAGE_KEYS
            if unknown:
                raise AICapabilityError(
                    f"modalité non prise en charge par ce client : {sorted(unknown)}",
                    user_message="Ce client n'envoie au modèle que du texte et des images. L'audio et la vidéo exigent un "
                    "prétraitement local ou une validation du runtime (prévu en phase 6).",
                )
            if message.get("images") and info.supports(CAP_VISION) is not True:
                raise AICapabilityError(
                    f"{model} n'annonce pas la vision",
                    user_message=f"Le modèle « {model} » n'annonce pas la prise en charge des images : aucune image n'a été envoyée.",
                )

    # ----- HTTP -----

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        timeout: float | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json", "User-Agent": f"AniFlow/{__version__}"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        try:
            response = self._transport.request(method, self.base_url + path, body=body, headers=headers, timeout=timeout or self._timeout)
        except TransportError as exc:
            raise AIUnavailableError(f"Ollama injoignable : {exc}", url=self.base_url) from exc
        if 300 <= response.status < 400:
            raise AINotLocalError(
                "redirection refusée",
                user_message="Le service IA a tenté de rediriger la requête : refusé, car seule l'IA locale est autorisée.",
            )
        try:
            data = json.loads(response.body.decode("utf-8")) if response.body else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            data = None
        if response.status == 404 and model is not None:
            raise AIModelMissingError(model)
        if not 200 <= response.status < 300:
            detail = data.get("error") if isinstance(data, Mapping) and isinstance(data.get("error"), str) else None
            raise AIResponseError(f"HTTP {response.status} sur {path}", detail=detail)
        if not isinstance(data, dict):
            raise AIResponseError(f"réponse JSON invalide sur {path}")
        return data


def _is_cloud(name: str) -> bool:
    try:
        ensure_not_cloud_name(name)
    except NotLocalError:
        return True
    return False
