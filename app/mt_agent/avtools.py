from __future__ import annotations

from pathlib import Path

from .ffx import run_ffmpeg


# Piste audio seule : AAC 192 kb/s dans un .m4a (lisible partout, CapCut compris).
def extract_audio(src: Path, out: Path) -> str:
    return run_ffmpeg(["-i", str(src), "-map", "0:a:0", "-vn", "-sn", "-dn", "-c:a", "aac", "-b:a", "192k"], out, "mp4")


# Vidéo seule : image copiée sans ré-encodage, aucune piste audio.
def remove_audio(src: Path, out: Path) -> str:
    return run_ffmpeg(["-i", str(src), "-map", "0:v:0", "-an", "-sn", "-dn", "-c:v", "copy"], out, "mp4")


_SIDE = 720  # côté commun après mise à l'échelle : hauteur (côte à côte) ou largeur (dessus, incrustation)
_CANVAS = (720, 1280)  # bout à bout : chaque vidéo tient dans ce cadre 9:16, barres noires
_PIP = 216  # incrustation : largeur de la vignette B (30 % de 720)
STACK_MODES = ("cote", "dessus", "bout", "incrust")


def _graph(mode: str) -> str:
    if mode in ("cote", "dessus"):
        sc = f"scale=-2:{_SIDE}" if mode == "cote" else f"scale={_SIDE}:-2"
        st = "hstack" if mode == "cote" else "vstack"
        return f"[0:v]{sc},fps=30,setsar=1[a];[1:v]{sc},fps=30,setsar=1[b];[a][b]{st}=inputs=2:shortest=1[v]"
    if mode == "bout":
        w, h = _CANVAS
        fit = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30"
        return f"[0:v]{fit}[a];[1:v]{fit}[b];[a][b]concat=n=2:v=1:a=0[v]"
    return (f"[0:v]scale={_SIDE}:-2,fps=30,setsar=1[a];"
            f"[1:v]scale={_PIP}:-2,setsar=1,pad=iw+6:ih+6:3:3:color=0x2b3fd6[b];"
            "[a][b]overlay=W-w-16:H-h-16:shortest=1[v]")


# Deux vidéos collées, sans son ; ré-encodage x264 (qualité Normal = crf 20).
def stack_videos(a: Path, b: Path, out: Path, mode: str) -> str:
    if mode not in STACK_MODES:
        raise ValueError(f"disposition inconnue: {mode}")
    return run_ffmpeg(["-i", str(a), "-i", str(b), "-filter_complex", _graph(mode), "-map", "[v]", "-an",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"], out, "mp4")
