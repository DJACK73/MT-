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
STACK_LIMITS = {"cote": (2, 3), "dessus": (2, 4), "bout": (2, 4), "incrust": (2, 2), "grille": (3, 4)}  # mode: (min, max) vidéos
STACK_MODES = tuple(STACK_LIMITS)
STACK_FITS = ("ajuster", "remplir")
FIT_MODES = ("bout", "grille")  # modes à cadre fixe : seuls concernés par le cadrage
_CELL = (360, 640)  # grille : cellule 9:16, 2×2 = 720×1280


def _fit(w: int, h: int, fit: str) -> str:
    # « remplir » recadre au centre (aucune barre noire) ; « ajuster » garde tout le plan, avec barres.
    if fit == "remplir":
        return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=30"
    return f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30"


def _chain(n: int, f: str) -> str:
    return ";".join(f"[{i}:v]{f}[v{i}]" for i in range(n)) + ";" + "".join(f"[v{i}]" for i in range(n))


def _graph(mode: str, n: int, fit: str) -> str:
    if mode in ("cote", "dessus"):
        sc = f"scale=-2:{_SIDE}" if mode == "cote" else f"scale={_SIDE}:-2"
        st = "hstack" if mode == "cote" else "vstack"
        base = sc + ",fps=30,setsar=1"
        return f"{_chain(n, base)}{st}=inputs={n}:shortest=1[v]"
    if mode == "bout":
        return f"{_chain(n, _fit(*_CANVAS, fit))}concat=n={n}:v=1:a=0[v]"
    if mode == "grille":
        layout = "|".join(("0_0", "w0_0", "0_h0", "w0_h0")[:n])
        return f"{_chain(n, _fit(*_CELL, fit))}xstack=inputs={n}:layout={layout}:shortest=1[v]"
    return (f"[0:v]scale={_SIDE}:-2,fps=30,setsar=1[a];"
            f"[1:v]scale={_PIP}:-2,setsar=1,pad=iw+6:ih+6:3:3:color=0x2b3fd6[b];"
            "[a][b]overlay=W-w-16:H-h-16:shortest=1[v]")


# 2 à 4 vidéos collées, sans son ; ré-encodage x264 (qualité Normal = crf 20).
def stack_videos(srcs: list[Path], out: Path, mode: str, fit: str = "ajuster") -> str:
    if mode not in STACK_LIMITS:
        raise ValueError(f"disposition inconnue: {mode}")
    if fit not in STACK_FITS:
        raise ValueError(f"cadrage inconnu: {fit}")
    lo, hi = STACK_LIMITS[mode]
    if not lo <= len(srcs) <= hi:
        raise ValueError(f"{mode}: {lo} à {hi} vidéos, reçu {len(srcs)}")
    ins = [x for s in srcs for x in ("-i", str(s))]
    return run_ffmpeg([*ins, "-filter_complex", _graph(mode, len(srcs), fit), "-map", "[v]", "-an",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"], out, "mp4")
