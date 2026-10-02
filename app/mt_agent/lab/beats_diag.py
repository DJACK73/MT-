from __future__ import annotations
import json, sys
import numpy as np
from .beats import _pcm, flux, pick, bpm, grid_from_onsets, cut_alignment
from .ffx import duration
from .scenes import detect_cuts

v = sys.argv[1]
f = flux(_pcm(v)); total = duration(v)
o = np.asarray(pick(f)); c, beats = grid_from_onsets(list(o), bpm(f), total)
p = 60 / c; b = np.asarray(beats)
d = np.abs(o[:, None] - b[None, :]).min(axis=1)
raw = detect_cuts(v, 0.35)
sweep = {ms: cut_alignment(raw, list(b + ms / 1000), p) for ms in range(-200, 201, 10)}
best = max(sweep, key=lambda k: sweep[k]["aligned_pct"])
print(json.dumps({
    "bpm": round(c, 1),
    "onsets_on_grid_pct": round(100 * float(np.mean(d <= 0.06)), 1),
    "onsets_chance_pct": round(100 * min(1.0, 0.12 / p), 1),
    "cuts_raw": len(raw),
    "aligned_at_zero_pct": sweep[0]["aligned_pct"],
    "best_shift_ms": best,
    "aligned_at_best_pct": sweep[best]["aligned_pct"],
    "chance_pct": sweep[0]["chance_pct"],
}, indent=2))
