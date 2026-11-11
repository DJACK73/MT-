from __future__ import annotations

from pathlib import Path

from .ffx import run_ffmpeg


# Piste audio seule : AAC 192 kb/s dans un .m4a (lisible partout, CapCut compris).
def extract_audio(src: Path, out: Path) -> str:
    return run_ffmpeg(["-i", str(src), "-map", "0:a:0", "-vn", "-sn", "-dn", "-c:a", "aac", "-b:a", "192k"], out, "mp4")


# Vidéo seule : image copiée sans ré-encodage, aucune piste audio.
def remove_audio(src: Path, out: Path) -> str:
    return run_ffmpeg(["-i", str(src), "-map", "0:v:0", "-an", "-sn", "-dn", "-c:v", "copy"], out, "mp4")


_SIDE = 720  # côté commun après mise à l'échelle : hauteur (côte à côte) ou largeur (empilées)


# Deux vidéos collées, sans son, durée de la plus courte ; ré-encodage x264 (qualité Normal = crf 20).
def stack_videos(a: Path, b: Path, out: Path, mode: str) -> str:
    if mode not in ("cote", "dessus"):
        raise ValueError(f"disposition inconnue: {mode}")
    sc = f"scale=-2:{_SIDE}" if mode == "cote" else f"scale={_SIDE}:-2"
    st = "hstack" if mode == "cote" else "vstack"
    fc = f"[0:v]{sc},fps=30,setsar=1[a];[1:v]{sc},fps=30,setsar=1[b];[a][b]{st}=inputs=2:shortest=1[v]"
    return run_ffmpeg(["-i", str(a), "-i", str(b), "-filter_complex", fc, "-map", "[v]", "-an",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"], out, "mp4")
