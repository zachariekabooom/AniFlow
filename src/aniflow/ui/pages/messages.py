"""Textes des pages non encore livrées (sans Qt) : toujours honnêtes, jamais de fonction simulée."""

from __future__ import annotations

from aniflow.ui.navigation import Section

IN_PROGRESS_PHASE = 1  # phase en cours (ROADMAP.md) ; à relever à chaque changement de phase


def placeholder_message(section: Section) -> tuple[str, str]:
    """(phrase principale, précision) d'une section dont le contenu n'existe pas encore."""
    if section.delivered_in <= IN_PROGRESS_PHASE:
        return (
            "Cette page n'est pas encore disponible.",
            f"Elle sera livrée lors d'une prochaine étape de la phase {section.delivered_in} du développement.",
        )
    return (
        "Cette section n'est pas encore disponible.",
        f"Elle est prévue à la phase {section.delivered_in} du développement d'AniFlow.",
    )
