from __future__ import annotations
import json, subprocess, sys
import numpy as np

SR, HOP, NFFT = 22050, 512, 1024

def _pcm(path: str) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)

def flux(y: np.ndarray, block: int = 2000, fmax: float | None = None) -> np.ndarray:
    win = np.hanning(NFFT).astype(np.float32)
    n = 1 + (len(y) - NFFT) // HOP
    out, prev = [], None
    for s in range(0, n, block):
        idx = (np.arange(s, min(n, s + block)) * HOP)[:, None] + np.arange(NFFT)[None, :]
        mag = np.log1p(np.abs(np.fft.rfft(y[idx] * win, axis=1)))[:, : (NFFT // 2 + 1 if fmax is None else int(fmax * NFFT / SR) + 1)]
        if prev is None:
            d = np.vstack([np.zeros((1, mag.shape[1])), np.diff(mag, axis=0)])
        else:
            d = np.diff(np.vstack([prev, mag]), axis=0)
        out.append(np.maximum(d, 0).sum(axis=1))
        prev = mag[-1:]
    return np.concatenate(out)

def pick(f: np.ndarray, min_gap_s: float = 0.25, k: float = 1.0) -> list[float]:
    w = int(SR / HOP)
    thr = np.convolve(f, np.ones(w) / w, mode="same") + k * f.std()
    gap, last, out = int(min_gap_s * SR / HOP), -10**9, []
    for i in range(1, len(f) - 1):
        if f[i] > thr[i] and f[i] >= f[i - 1] and f[i] >= f[i + 1] and i - last >= gap:
            out.append(i * HOP / SR); last = i
    return out

def bpm(f: np.ndarray, lo: int = 60, hi: int = 180) -> float:
    x = f - f.mean()
    n = 1 << (2 * len(x) - 1).bit_length()
    ac = np.fft.irfft(np.abs(np.fft.rfft(x, n)) ** 2)[: len(x)]
    fps = SR / HOP
    lags = np.arange(int(fps * 60 / hi), int(fps * 60 / lo) + 1)
    return round(60 * fps / lags[np.argmax(ac[lags])], 1)

def _lift(o: np.ndarray, p: float, phi: float, tol: float) -> float:
    d = (o - phi + p / 2) % p - p / 2
    return float(np.mean(np.abs(d) <= tol)) / min(1.0, 2 * tol / p)

def grid_from_onsets(onsets: list[float], bpm0: float, total: float, tol: float = 0.06,
                     prefer: tuple[float, float] = (80.0, 160.0)) -> tuple[float, list[float]]:
    o = np.asarray(onsets)
    best = (0.0, bpm0, 0.0)
    for base in (bpm0 / 2, bpm0, bpm0 * 2):
        if not 50 <= base <= 200:
            continue
        for c in base * np.linspace(0.97, 1.03, 13):
            p = 60 / c
            bonus = 1.1 if prefer[0] <= c <= prefer[1] else 1.0
            for phi in np.linspace(0, p, 40, endpoint=False):
                s = _lift(o, p, phi, tol) * bonus
                if s > best[0]:
                    best = (s, float(c), float(phi))
    _, c, phi = best
    return c, [float(t) for t in np.arange(phi, total, 60 / c)]

def _phase_lock(onsets: list[float], c: float, total: float, tol: float = 0.05) -> tuple[float, list[float]]:
    o, p = np.asarray(onsets), 60 / c
    phi = max(np.linspace(0, p, 120, endpoint=False), key=lambda x: _lift(o, p, float(x), tol))
    return c, [float(t) for t in np.arange(phi, total, p)]

def _numpy_backend(path: str) -> tuple[float, list[float]]:
    y = _pcm(path); total = len(y) / SR
    f = flux(y)
    c, _ = grid_from_onsets(pick(f), bpm(f), total)      # tempo : bande complète
    low = pick(flux(y, fmax=200.0))                       # phase : basses (grosse caisse)
    return _phase_lock(low or pick(f), c, total)

def _librosa_backend(path: str) -> tuple[float, list[float]]:
    import librosa  # optionnel : pip install librosa (compatibilité Python 3.14 non vérifiée)
    y, sr = librosa.load(path, sr=22050, mono=True)
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr)
    return float(np.atleast_1d(tempo)[0]), librosa.frames_to_time(frames, sr=sr).tolist()

BACKENDS = {"numpy": _numpy_backend, "librosa": _librosa_backend}

def cut_alignment(cuts: list[float], beats: list[float], period: float, tol: float = 0.08) -> dict:
    d = np.abs(np.asarray(cuts)[:, None] - np.asarray(beats)[None, :]).min(axis=1)
    return {"cuts": len(cuts), "aligned_pct": round(100 * float(np.mean(d <= tol)), 1),
            "chance_pct": round(100 * min(1.0, 2 * tol / period), 1),
            "median_offset_ms": round(float(np.median(d)) * 1000)}

if __name__ == "__main__":
    import argparse
    from .ffx import duration
    from .scenes import detect_cuts, to_scenes
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--backend", default="numpy", choices=list(BACKENDS))
    a = ap.parse_args()
    c, beats = BACKENDS[a.backend](a.video)
    cuts = [s for s, _ in to_scenes(detect_cuts(a.video), duration(a.video), 1.0)][1:]
    print(json.dumps({"backend": a.backend, "bpm": round(c, 1), "beats": len(beats),
                      "first": [round(t, 2) for t in beats[:8]],
                      "alignment": cut_alignment(cuts, beats, 60 / c)}, indent=2))
