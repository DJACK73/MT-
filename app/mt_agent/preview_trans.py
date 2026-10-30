"""Aperçu d'une transition : jonction a -> b (ctx s de a, transition, ctx s de b), mp4 basse résolution caché.
Ne touche pas à preview.py. Sans cadrage final, sans effets ni étalonnage (patch séparé)."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .export import TRANS
from .ffx import run_ffmpeg
from .paths import ensure_outside_inbox
from .preview import _zoom_crop

XFADE = frozenset(v for v in TRANS.values() if v)


@dataclass(frozen=True)
class Seg:
    """Une scène vue par l'aperçu : source, bornes (s, dans la source) et réglages visuels de la scène."""
    src: Path
    start: float
    end: float
    mirror: bool = False
    zoom: float = 1.0


def _frame_size(src: Path) -> tuple[int, int]:
    """(largeur, hauteur) affichées, rotation comprise ; ffprobe requis."""
    exe = shutil.which("ffprobe")
    if exe is None:
        raise FileNotFoundError("ffprobe introuvable")
    r = subprocess.run([exe, "-v", "error", "-select_streams", "v:0", "-of", "json", "-show_entries",
                        "stream=width,height:stream_tags=rotate:stream_side_data=rotation", str(src)],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    rot = float(s.get("tags", {}).get("rotate", 0))
    for sd in s.get("side_data_list", []):
        rot = float(sd.get("rotation", rot))
    w, h = int(s["width"]), int(s["height"])
    return (h, w) if round(abs(rot)) % 180 == 90 else (w, h)


def trans_key(a: Seg, b: Seg, tr: str, td: float, speed: float = 1.0, width: int = 360, ctx: float = 1.0) -> str:
    """Clé de cache : tout ce qui change l'image (sources + mtime, bornes, miroir, zoom, transition, durée, vitesse, taille)."""
    def one(s: Seg) -> str:
        return f"{s.src}|{s.src.stat().st_mtime_ns}|{s.start:.3f}|{s.end:.3f}|{int(s.mirror)}|{s.zoom:g}"
    raw = f"T|{one(a)}|{one(b)}|{tr}|{td:g}|{speed:g}|{width}|{ctx:g}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _chain(s: Seg, speed: float, w: int, h: int) -> str:
    """Même ordre que preview_clip (vitesse, miroir, zoom), puis cadre commun w x h (xfade exige taille/fps/timebase égaux)."""
    return (f"setpts=(PTS-STARTPTS)/{speed:g},fps=25," + ("hflip," if s.mirror else "") + _zoom_crop(s.zoom)
            + f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,format=yuv420p,settb=AVTB")


def preview_trans(a: Seg, b: Seg, root: Path, tr: str, td: float, speed: float = 1.0,
                  width: int = 360, ctx: float = 1.0) -> Path:
    """MP4 sans audio de la jonction a -> b, caché dans workspace/previews/. tr = nom xfade (valeur de TRANS). Jamais d'écrasement."""
    if tr not in XFADE:
        raise ValueError(f"transition inconnue: {tr}")
    if not 0.1 <= td <= 1.0:
        raise ValueError(f"durée de transition hors de 0.1..1 s: {td}")
    if not 0.5 <= speed <= 2.0:
        raise ValueError(f"vitesse hors 0,5..2: {speed}")
    for s in (a, b):
        if not s.src.is_file():
            raise FileNotFoundError(f"source absente: {s.src}")
        if not 0 <= s.start < s.end:
            raise ValueError(f"bornes invalides: {s.start}..{s.end}")
    la = min(ctx + td, (a.end - a.start) / speed)  # durées de sortie
    lb = min(ctx + td, (b.end - b.start) / speed)
    if min(la, lb) < td:
        raise ValueError(f"scène trop courte pour une transition de {td:g} s")
    out_dir = ensure_outside_inbox(root / "workspace" / "previews", root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"trans-{trans_key(a, b, tr, td, speed, width, ctx)}.mp4"
    if not out.exists():
        sw, sh = _frame_size(a.src)
        w, h = width // 2 * 2, max(2, round(width * sh / sw / 2) * 2)
        g = (f"[0:v]{_chain(a, speed, w, h)}[a];[1:v]{_chain(b, speed, w, h)}[b];"
             f"[a][b]xfade=transition={tr}:duration={td:g}:offset={la - td:.3f}[v]")
        run_ffmpeg(["-ss", f"{a.end - la * speed:.3f}", "-t", f"{la * speed:.3f}", "-i", str(a.src),
                    "-ss", f"{b.start:.3f}", "-t", f"{lb * speed:.3f}", "-i", str(b.src), "-an",
                    "-filter_complex", g, "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast",
                    "-crf", "30", "-movflags", "+faststart"], out, fmt="mp4")
    return out
