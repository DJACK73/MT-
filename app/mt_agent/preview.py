from __future__ import annotations
import hashlib
from pathlib import Path
from .ffx import run_ffmpeg
from .paths import ensure_outside_inbox

def _zoom_crop(zoom: float) -> str:
    """Même crop centré que export._node ; vide si zoom = 1."""
    if not 1.0 <= zoom <= 2.0:
        raise ValueError(f"zoom hors de 1..2: {zoom}")
    return "" if zoom == 1.0 else f"crop=trunc(iw/{zoom:g}/2)*2:trunc(ih/{zoom:g}/2)*2,"


def preview_key(src: Path, start: float, end: float, width: int, mirror: bool = False,
                zoom: float = 1.0) -> str:
    raw = (f"{src}|{src.stat().st_mtime_ns}|{start:.3f}|{end:.3f}|{width}" + ("|m" if mirror else "")
           + (f"|z{zoom:g}" if zoom != 1.0 else ""))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def preview_clip(src: Path, start: float, end: float, root: Path, width: int = 480, mirror: bool = False,
                 zoom: float = 1.0) -> Path:
    """MP4 basse résolution sans audio de [start, end], caché dans workspace/previews/. Jamais d'écrasement."""
    if not src.is_file():
        raise FileNotFoundError(f"source absente: {src}")
    if not 0 <= start < end:
        raise ValueError(f"bornes invalides: {start}..{end}")
    out_dir = ensure_outside_inbox(root / "workspace" / "previews", root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{preview_key(src, start, end, width, mirror, zoom)}.mp4"
    if not out.exists():
        run_ffmpeg(["-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(src), "-an",
                    "-vf", ("hflip," if mirror else "") + _zoom_crop(zoom) + f"scale={width}:-2,format=yuv420p", "-c:v", "libx264",
                    "-preset", "ultrafast", "-crf", "30", "-movflags", "+faststart"], out, fmt="mp4")
    return out
