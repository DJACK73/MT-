from __future__ import annotations
import re
from .ffx import run_ffmpeg

_T = re.compile(r"pts_time:([\d.]+)")

def detect_cuts(path: str, threshold: float = 0.35) -> list[float]:
    vf = f"scale=320:-2,select='gt(scene,{threshold})',showinfo"
    log = run_ffmpeg(["-i", path, "-vf", vf, "-an", "-f", "null", "-"])
    return sorted({float(m[1]) for line in log.splitlines() if (m := _T.search(line))})

def to_scenes(cuts: list[float], total: float, min_s: float) -> list[tuple[float, float]]:
    bounds = [0.0, *[c for c in cuts if 0 < c < total], total]
    merged: list[list[float]] = []
    for a, b in zip(bounds, bounds[1:]):
        if merged and b - a < min_s:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    if len(merged) > 1 and merged[0][1] - merged[0][0] < min_s:
        merged[1][0] = merged[0][0]; merged.pop(0)
    return [(a, b) for a, b in merged]
