#!/usr/bin/env python3
"""Sonde phase 0 — libmpv via python-mpv : lecture, pause, ±15 s, reprise de position.

    python tools/phase0/mpv_probe.py --file reports/test-60s.mp4 --dll-dir third_party/libmpv --headless --out reports/mpv.json

--headless : aucune fenêtre ni son (vo=null, ao=null), idéal pour une vérification automatique.
Sans --headless : lecture dans la fenêtre autonome de mpv avec son (contrôle visuel).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import emit, environment

from aniflow.services.player.probe import prepare_dll_search_path, run_probe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", required=True, help="vidéo de test (voir make_test_media.py)")
    parser.add_argument("--dll-dir", help="dossier contenant libmpv-2.dll")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.dll_dir and not Path(args.dll_dir).is_dir():
        print(f"Dossier introuvable : {args.dll_dir}. Créez-le et placez-y libmpv-2.dll (voir docs/phase0/validation-windows.md).", file=sys.stderr)
        return 2
    prepare_dll_search_path(args.dll_dir)
    try:
        import mpv  # noqa: PLC0415 — après la préparation du PATH, exigée par python-mpv
    except ModuleNotFoundError:
        print("Module « mpv » introuvable. Installez-le : pip install mpv   (ou : pip install -e .[player])", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"libmpv-2.dll introuvable ou illisible ({exc}).\n"
              "Placez libmpv-2.dll (archive mpv-dev-x86_64-*.7z) dans third_party/libmpv puis relancez avec --dll-dir third_party/libmpv.\n"
              "Vérifiez aussi que Python et la DLL ont la même architecture (64 bits).", file=sys.stderr)
        return 2

    report = run_probe(mpv, args.file, headless=args.headless)
    report.update(environment())
    emit(report, args.out)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
