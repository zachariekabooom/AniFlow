#!/usr/bin/env python3
"""Sonde phase 0 — Ollama local : version, modèles installés, capacités réelles, débit, mémoire.

    python tools/phase0/ollama_probe.py --model gemma4:e2b --out reports/ollama-e2b.json

N'installe et ne télécharge aucun modèle. Refuse toute adresse non locale et tout modèle « cloud ».
Conseil : démarrez Ollama avec OLLAMA_NO_CLOUD=1 pour désactiver ses fonctions cloud (FAQ Ollama).
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from _common import emit, environment

from aniflow.net.local_only import DEFAULT_OLLAMA_URL
from aniflow.services.ai import AIError, OllamaClient

SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--model", help="modèle à tester (ex. gemma4:e2b) ; sans lui, seul l'inventaire est fait")
    parser.add_argument("--no-chat", action="store_true", help="ne pas lancer la génération de test")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    steps: list[dict[str, Any]] = []

    def record(name: str, ok: bool, **details: Any) -> None:
        steps.append({"name": name, "ok": ok, "details": details})

    try:
        client = OllamaClient(args.url)
    except AIError as exc:
        record("adresse_locale", False, erreur=exc.user_message)
        client = None

    if client is not None:
        try:
            record("version", True, version=client.version())
            models = client.list_models()
            record("modèles_installés", True, modèles=[{"nom": m.name, "taille_Go": None if m.size_bytes is None else round(m.size_bytes / 1e9, 2), "paramètres": m.parameter_size,
                                                        "quantification": m.quantization, "distant_donc_interdit": m.is_remote} for m in models])
            if args.model:
                status = client.check_ready(args.model)
                record("état_du_modèle", status.ok, état=status.state, message=status.message, capacités=list(status.capabilities))
                if status.ok:
                    info = client.ensure_usable(args.model)
                    record("modalités", True, vision=info.supports("vision"), audio=info.supports("audio"), thinking=info.supports("thinking"), contexte_max=info.context_length)
                    if not args.no_chat:
                        started = time.perf_counter()
                        result = client.chat_json(args.model, [{"role": "user", "content": 'Réponds uniquement par un objet JSON {"answer": "ok"}.'}], schema=SCHEMA, options={"temperature": 0, "num_ctx": 2048}, think=False)
                        m = result.metrics
                        record("génération_structurée", isinstance(result.data, dict) and "answer" in result.data, réponse=result.data, durée_mur_s=round(time.perf_counter() - started, 2),
                               chargement_s=m.load_seconds, jetons_prompt=m.prompt_tokens, jetons_générés=m.completion_tokens, jetons_par_seconde=None if m.tokens_per_second is None else round(m.tokens_per_second, 1))
                        running = [r for r in client.running() if r.name.split(":")[0] == args.model.split(":")[0]]
                        record("mémoire_en_cours", bool(running), modèles_chargés=[{"nom": r.name, "taille_Go": None if r.size_bytes is None else round(r.size_bytes / 1e9, 2),
                                                                                    "dont_VRAM_Go": None if r.size_vram_bytes is None else round(r.size_vram_bytes / 1e9, 2)} for r in client.running()])
        except AIError as exc:
            record("erreur", False, erreur=exc.user_message, technique=str(exc))

    report = {"tool": "ollama_probe", "ok": bool(steps) and all(s["ok"] for s in steps), **environment(), "url": args.url, "model": args.model, "steps": steps}
    emit(report, args.out)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
