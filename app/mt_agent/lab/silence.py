from __future__ import annotations
import re
from .ffx import run_ffmpeg, duration

_S = re.compile(r"silence_start:\s*(-?\d+(?:\.\d+)?)")
_E = re.compile(r"silence_end:\s*(-?\d+(?:\.\d+)?)")

def detect_silences(path: str, noise_db: float = -35.0, min_s: float = 0.5) -> list[tuple[float, float]]:
    log = run_ffmpeg(["-i", path, "-vn", "-af", f"silencedetect=noise={noise_db}dB:d={min_s}", "-f", "null", "-"])
    out: list[tuple[float, float]] = []
    start: float | None = None
    for line in log.splitlines():
        if m := _S.search(line):
            start = max(0.0, float(m[1]))
        elif (m := _E.search(line)) and start is not None:
            out.append((start, float(m[1]))); start = None
    if start is not None:
        out.append((start, duration(path)))
    return out

def snap_to_silence(t: float, silences: list[tuple[float, float]], tol: float = 0.4) -> float:
    mids = [(a + b) / 2 for a, b in silences]
    best = min(mids, key=lambda m: abs(m - t), default=t)
    return best if abs(best - t) <= tol else t
