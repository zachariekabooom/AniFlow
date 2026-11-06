"""Contrôles du mode --smoke-test, sans Qt : transforment des constats en problèmes lisibles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SmokeFacts:
    window_visible: bool
    sections_shown: int  # pages dans la pile
    sections_expected: int
    navigation_in_sync: bool  # page affichée et entrée cochée = section courante
    theme_applied: bool  # feuille de style non vide
    lc_numeric: str
    base_style: str  # style de base noté par apply_theme : « fusion » attendu
    style_warnings: tuple[str, ...] = ()


def smoke_problems(facts: SmokeFacts) -> list[str]:
    problems: list[str] = []
    if not facts.window_visible:
        problems.append("la fenêtre principale n'est pas visible")
    if facts.sections_shown != facts.sections_expected:
        problems.append(f"{facts.sections_shown} page(s) affichable(s) au lieu de {facts.sections_expected}")
    if not facts.navigation_in_sync:
        problems.append("la page affichée ne correspond pas à la section courante")
    if not facts.theme_applied:
        problems.append("le thème sombre n'est pas appliqué")
    if facts.base_style != "fusion":
        problems.append(f"le style de base n'est pas Fusion (obtenu : « {facts.base_style or 'inconnu'} »)")
    if facts.lc_numeric != "C":
        problems.append(f"LC_NUMERIC vaut « {facts.lc_numeric} » au lieu de « C » (incompatible avec libmpv)")
    problems.extend(f"avertissement de style Qt : {warning}" for warning in facts.style_warnings)
    return problems
