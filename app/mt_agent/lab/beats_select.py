from __future__ import annotations
import json, sys, wave
from pathlib import Path
import numpy as np
from .beats import BACKENDS, SR, _pcm, flux, pick

def grid_score(onsets: list[float], beats: list[float], tol: float = 0.06) -> float:
    o, b = np.asarray(onsets), np.asarray(beats)
    return float(np.mean(np.abs(o[:, None] - b[None, :]).min(axis=1) <= tol))

def consensus(path: str) -> dict:
    onsets = pick(flux(_pcm(path)))
    found: dict[str, dict] = {}
    for name, fn in BACKENDS.items():
        try:
            c, b = fn(path)
        except ImportError:
            continue
        found[name] = {"bpm": round(c, 1), "beats": b, "score": grid_score(onsets, b)}
    best = max(found, key=lambda k: found[k]["score"])
    bpms = [v["bpm"] for v in found.values()]
    agree = len(bpms) > 1 and any(abs(bpms[0] / (bpms[1] * f) - 1) < 0.03 for f in (0.5, 1, 2))
    return {"best": best,
            "confidence": "high" if agree else ("single" if len(found) == 1 else "low"),
            "candidates": {k: {"bpm": v["bpm"], "score": round(v["score"], 3)} for k, v in found.items()},
            "beats": found[best]["beats"]}

def synth(bpm: float, dur: float = 60.0) -> tuple[np.ndarray, list[float]]:
    rng = np.random.default_rng(0)
    n = int(dur * SR)
    y = rng.normal(0, 0.02, n).astype(np.float32)
    kt = np.arange(int(0.08 * SR)) / SR
    kick = (np.sin(2 * np.pi * 70 * kt) * np.exp(-kt * 40)).astype(np.float32)
    hl = int(0.02 * SR)
    hat = (rng.normal(0, 0.3, hl) * np.hanning(hl)).astype(np.float32)
    p, t, truth = 60 / bpm, 0.25, []
    while t < dur - 0.3:
        i = int(t * SR); y[i:i + len(kick)] += kick; truth.append(t)
        j = int((t + p / 2) * SR); y[j:j + hl] += hat
        t += p
    return y, truth

def selftest() -> None:
    Path("workspace/lab").mkdir(parents=True, exist_ok=True)
    for bpm in (90, 120, 140):
        y, truth = synth(bpm)
        path = f"workspace/lab/synth_{bpm}.wav"
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
        for name, fn in BACKENDS.items():
            try:
                c, b = fn(path)
            except ImportError:
                print(f"{bpm} BPM | {name}: non installé, ignoré"); continue
            octave_err = min(abs(c / f - bpm) / bpm for f in (0.5, 1, 2)) * 100
            phase_ms = float(np.median(np.abs(np.asarray(truth)[:, None] - np.asarray(b)[None, :]).min(axis=1))) * 1000
            print(f"{bpm} BPM | {name}: estimé {c:.1f} | erreur (octave tolérée) {octave_err:.1f}% | décalage médian {phase_ms:.0f} ms")

if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        selftest()
    else:
        r = consensus(sys.argv[2]); r["beats"] = len(r["beats"])
        print(json.dumps(r, indent=2))
