from __future__ import annotations

from pathlib import Path

from .ffx import run_ffmpeg


# Piste audio seule : AAC 192 kb/s dans un .m4a (lisible partout, CapCut compris).
def extract_audio(src: Path, out: Path) -> str:
    return run_ffmpeg(["-i", str(src), "-map", "0:a:0", "-vn", "-sn", "-dn", "-c:a", "aac", "-b:a", "192k"], out, "mp4")


# Vidéo seule : image copiée sans ré-encodage, aucune piste audio.
def remove_audio(src: Path, out: Path) -> str:
    return run_ffmpeg(["-i", str(src), "-map", "0:v:0", "-an", "-sn", "-dn", "-c:v", "copy"], out, "mp4")
