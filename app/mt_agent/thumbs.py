from __future__ import annotations
import hashlib, json, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .approval import PlanError
from .ffx import MediaError, run_ffmpeg
from .models import Plan
from .paths import ensure_outside_inbox

def thumbs_key(plan: Plan) -> str:
    """Clé = sources + bornes des scènes. Changer la sélection ne régénère rien."""
    d = {"s": [(s.id, s.path) for s in plan.sources], "b": [(c.source_id, c.start, c.end) for c in plan.scenes]}
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]

def make_thumbnails(plan: Plan, root: Path, width: int = 320) -> list[Path | None]:
    """Une vignette JPEG par scène (milieu), dans workspace/thumbs/<clé>/NNN.jpg. Jamais d'écrasement. None si ffmpeg échoue pour cette scène."""
    out_dir = ensure_outside_inbox(root / "workspace" / "thumbs" / thumbs_key(plan), root)
    out_dir.mkdir(parents=True, exist_ok=True)
    srcs = {s.id: (Path(s.path) if Path(s.path).is_absolute() else root / s.path) for s in plan.sources}
    jobs: list[tuple[Path, float, Path]] = []
    for i, sc in enumerate(plan.scenes, 1):
        src = srcs.get(sc.source_id)
        if src is None or not src.is_file():
            raise PlanError(f"source absente: {sc.source_id}")
        jobs.append((src, (sc.start + sc.end) / 2, out_dir / f"{i:03d}.jpg"))

    def one(job: tuple[Path, float, Path]) -> Path | None:
        src, mid, out = job
        if not out.exists():
            try:
                run_ffmpeg(["-ss", f"{mid:.3f}", "-i", str(src), "-frames:v", "1",
                            "-vf", f"scale={width}:-2,format=yuvj420p", "-c:v", "mjpeg", "-q:v", "3", "-update", "1"],
                           out, fmt="image2")
            except MediaError:
                pass  # échec ou course : vignette absente = None, jamais d'exception
        return out if out.exists() else None

    with ThreadPoolExecutor(max_workers=max(1, min(4, os.cpu_count() or 1))) as ex:
        return list(ex.map(one, jobs))  # map conserve l'ordre des scènes
