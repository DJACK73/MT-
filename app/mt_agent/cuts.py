from __future__ import annotations
import re
from .ffx import run_ffmpeg

_T = re.compile(r"pts_time:([\d.]+)")

def detect_cuts(path: str, threshold: float = 0.35) -> list[float]:
    if not 0 < threshold < 1:
        raise ValueError("threshold dans ]0,1[")
    vf = f"scale=320:-2,select='gt(scene,{threshold})',showinfo"
    log = run_ffmpeg(["-i", path, "-vf", vf, "-an", "-f", "null", "-"])
    return sorted({float(m[1]) for line in log.splitlines() if (m := _T.search(line))})
