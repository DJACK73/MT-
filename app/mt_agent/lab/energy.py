from __future__ import annotations
import re
from .ffx import run_ffmpeg

_L = re.compile(r"t:\s*([\d.]+)\s.*?\bM:\s*(-?[\d.]+|-inf)")

def energy_profile(path: str) -> list[tuple[float, float]]:
    log = run_ffmpeg(["-i", path, "-vn", "-af", "ebur128=framelog=info", "-f", "null", "-"])
    return [(float(m[1]), -70.0 if m[2] == "-inf" else float(m[2]))
            for line in log.splitlines() if (m := _L.search(line))]

def peaks(profile: list[tuple[float, float]], n: int = 5, min_gap: float = 5.0) -> list[tuple[float, float]]:
    chosen: list[tuple[float, float]] = []
    for t, v in sorted(profile, key=lambda p: p[1], reverse=True):
        if all(abs(t - c) >= min_gap for c, _ in chosen):
            chosen.append((t, v))
        if len(chosen) == n:
            break
    return chosen

def scene_energy(scenes: list[tuple[float, float]], profile: list[tuple[float, float]]) -> list[float]:
    return [sum(v for t, v in profile if a <= t < b) / max(1, sum(1 for t, _ in profile if a <= t < b))
            for a, b in scenes]
