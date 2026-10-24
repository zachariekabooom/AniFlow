#!/usr/bin/env python3
"""Génère une vidéo de test synthétique (mire + sinus 440 Hz) avec FFmpeg : légale, légère, reproductible.

    python tools/phase0/make_test_media.py --out reports/test-60s.mp4 --seconds 60
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def build_command(ffmpeg: str, out: Path, seconds: int, video_codec: str) -> list[str]:
    return [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-t", str(seconds), "-c:v", video_codec, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k", "-shortest", str(out),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="reports/test-60s.mp4")
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args(argv)

    ffmpeg = shutil.which(args.ffmpeg)
    if not ffmpeg:
        print("FFmpeg introuvable dans le PATH. Installez-le (https://ffmpeg.org/download.html) ou utilisez --ffmpeg <chemin>.", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for codec in ("libx264", "mpeg4"):  # repli si cette build de FFmpeg n'embarque pas x264
        result = subprocess.run(build_command(ffmpeg, out, args.seconds, codec), capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Vidéo de test créée : {out} ({out.stat().st_size / 1024:.0f} Ko, codec vidéo {codec})")
            return 0
    print(f"Échec de FFmpeg : {result.stderr.strip()}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
