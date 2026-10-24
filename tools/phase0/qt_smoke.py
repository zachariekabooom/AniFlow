#!/usr/bin/env python3
"""Sonde phase 0 — PySide6 : thème sombre AniFlow, logo approuvé et (option) libmpv intégré à une fenêtre Qt.

    python tools/phase0/qt_smoke.py                                   # thème + logo seulement
    python tools/phase0/qt_smoke.py --video reports/test-60s.mp4 --dll-dir third_party/libmpv

Contrôle visuel : fond bleu marine, logo visible, vidéo dans le cadre, boutons Lecture/Pause, −15 s, +15 s
fonctionnels, compteur de position qui avance. Utilisez --auto-quit-ms 5000 pour une fermeture automatique.
"""

from __future__ import annotations

import argparse
import locale
import sys
from pathlib import Path

from _common import emit, environment

from aniflow.paths import logo_path
from aniflow.services.player.probe import prepare_dll_search_path
from aniflow.ui.theme import build_stylesheet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video")
    parser.add_argument("--dll-dir")
    parser.add_argument("--auto-quit-ms", type=int, default=0)
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.dll_dir and not Path(args.dll_dir).is_dir():
        print(f"Dossier introuvable : {args.dll_dir}. Créez-le et placez-y libmpv-2.dll (voir docs/phase0/validation-windows.md).", file=sys.stderr)
        return 2
    prepare_dll_search_path(args.dll_dir)
    try:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
    except ImportError:
        print("PySide6 introuvable. Installez-le : pip install PySide6   (ou : pip install -e .[ui])", file=sys.stderr)
        return 2

    app = QApplication(sys.argv)
    locale.setlocale(locale.LC_NUMERIC, "C")  # Qt modifie la locale ; libmpv exige LC_NUMERIC = C
    app.setStyleSheet(build_stylesheet())

    window = QWidget()
    window.setWindowTitle("AniFlow — sonde Qt (phase 0)")
    window.resize(960, 640)
    layout = QVBoxLayout(window)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(16)

    logo = QLabel()
    path = logo_path()
    pixmap = QPixmap(str(path)) if path else QPixmap()
    logo_loaded = not pixmap.isNull()
    if logo_loaded:
        logo.setPixmap(pixmap.scaledToHeight(96, Qt.TransformationMode.SmoothTransformation))
    else:
        logo.setText("Logo introuvable : docs/branding/aniflow-logo-final.png")
        logo.setProperty("role", "error")
    layout.addWidget(logo)

    title = QLabel("AniFlow — vérification du thème et du lecteur")
    title.setProperty("role", "title")
    layout.addWidget(title)

    report: dict = {"tool": "qt_smoke", **environment(), "logo_loaded": logo_loaded, "mpv": None}
    player = None
    timer = QTimer()

    if args.video:
        try:
            import mpv
        except (ModuleNotFoundError, OSError) as exc:
            report["mpv"] = {"ok": False, "error": repr(exc)}
        else:
            surface = QWidget()
            surface.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
            surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
            surface.setMinimumHeight(360)
            layout.addWidget(surface, 1)
            status = QLabel("—")
            status.setProperty("role", "muted")
            controls = QHBoxLayout()
            buttons = {}
            for key, label in (("toggle", "Lecture / Pause"), ("back", "−15 s"), ("forward", "+15 s")):
                buttons[key] = QPushButton(label)
                controls.addWidget(buttons[key])
            controls.addWidget(status, 1)
            layout.addLayout(controls)
            window.show()  # l'identifiant natif de la fenêtre doit exister avant de créer le lecteur
            player = mpv.MPV(wid=str(int(surface.winId())), vo="gpu", input_default_bindings=False, osc=False, log_handler=lambda lvl, pre, txt: None, loglevel="warn")
            player.play(args.video)
            buttons["toggle"].clicked.connect(lambda: setattr(player, "pause", not player.pause))
            buttons["back"].clicked.connect(lambda: player.seek(-15, reference="relative"))
            buttons["forward"].clicked.connect(lambda: player.seek(15, reference="relative"))
            samples: list[float] = []

            def refresh() -> None:
                pos, dur = player.time_pos, player.duration
                if pos is not None:
                    samples.append(pos)
                    status.setText(f"{pos:6.1f} s / {dur or 0:6.1f} s" + ("  (pause)" if player.pause else ""))

            timer.timeout.connect(refresh)
            timer.start(250)
            report["mpv"] = {"ok": None, "note": "à confirmer visuellement ; positions échantillonnées ci-dessous", "samples": samples}

    window.show()
    if args.auto_quit_ms > 0:
        QTimer.singleShot(args.auto_quit_ms, app.quit)
    code = app.exec()
    timer.stop()
    if player is not None:
        if report["mpv"] is not None:
            samples = report["mpv"]["samples"]
            report["mpv"]["ok"] = len(samples) >= 2 and samples[-1] > samples[0]
            report["mpv"]["samples"] = [round(s, 2) for s in samples[:: max(1, len(samples) // 10)]]
        player.terminate()
    report["ok"] = bool(logo_loaded) and (report["mpv"] is None or bool(report["mpv"].get("ok")))
    emit(report, args.out)
    return code or (0 if report["ok"] else 1)


if __name__ == "__main__":
    sys.exit(main())
