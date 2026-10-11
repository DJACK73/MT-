"""Battements d'un morceau : grille à tempo constant, cache, calage des durées de scène."""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
import numpy as np

SR, HOP, NFFT = 22050, 512, 1024
_V = 1  # à changer si l'algorithme change : invalide le cache


def _pcm(path: str) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


def _flux(y: np.ndarray, block: int = 2000, fmax: float | None = None) -> np.ndarray:
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


def _pick(f: np.ndarray, min_gap_s: float = 0.25, k: float = 1.0) -> list[float]:
    w = int(SR / HOP)
    thr = np.convolve(f, np.ones(w) / w, mode="same") + k * f.std()
    gap, last, out = int(min_gap_s * SR / HOP), -10**9, []
    for i in range(1, len(f) - 1):
        if f[i] > thr[i] and f[i] >= f[i - 1] and f[i] >= f[i + 1] and i - last >= gap:
            out.append((i * HOP + NFFT / 2) / SR)  # centre de la trame, pas son début (biais mesuré : -27 ms)
            last = i
    return out


def _tempo(f: np.ndarray, lo: int = 60, hi: int = 180) -> float:
    x = f - f.mean()
    n = 1 << (2 * len(x) - 1).bit_length()
    ac = np.fft.irfft(np.abs(np.fft.rfft(x, n)) ** 2)[: len(x)]
    fps = SR / HOP
    lags = np.arange(int(fps * 60 / hi), int(fps * 60 / lo) + 1)
    return round(60 * fps / lags[np.argmax(ac[lags])], 1)


def _lift(o: np.ndarray, p: float, phi: float, tol: float) -> float:
    d = (o - phi + p / 2) % p - p / 2
    return float(np.mean(np.abs(d) <= tol)) / min(1.0, 2 * tol / p)


def _grid_from_onsets(onsets: list[float], bpm0: float, total: float, tol: float = 0.06,
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


def grid_from_pcm(y: np.ndarray) -> tuple[float, list[float]]:
    """(BPM, temps des battements en s) d'un signal mono à SR Hz ; (0.0, []) si rien de fiable.
    Tempo : bande complète. Phase : basses (min 0,15 s entre attaques). Période et phase affinées par régression."""
    total = len(y) / SR
    if total < 5:
        return 0.0, []
    f = _flux(y)
    onsets = _pick(f)
    if len(onsets) < 8:
        return 0.0, []
    c, _ = _grid_from_onsets(onsets, _tempo(f), total)
    on = np.asarray(_pick(_flux(y, fmax=200.0), min_gap_s=0.15))
    if len(on) < 8:
        return 0.0, []
    _, g = _phase_lock(list(on), c, total)
    if len(g) < 2:
        return 0.0, []
    p, g0 = 60 / c, g[0]
    idx = np.rint((on - g0) / p).astype(int)
    res = on - (g0 + idx * p)
    keep = np.abs(res - np.median(res)) <= 0.05
    if keep.sum() < 8:
        return c, g
    s, i0 = np.polyfit(idx[keep], on[keep], 1)
    r = i0 + s * np.arange(int(total / s) + 1)
    return 60 / s, [float(t) for t in r[(r >= 0) & (r < total)]]


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute(path: str) -> tuple[float, list[float], float]:
    y = _pcm(path)
    c, g = grid_from_pcm(y)
    return c, g, len(y) / SR


def analyse(path: Path, cache_dir: Path) -> dict:
    """{"bpm", "beats", "length"} d'un morceau ; cache = hash du contenu du fichier. bpm 0.0 = non fiable."""
    f = cache_dir / f"{_digest(path)[:16]}-v{_V}.json"
    if f.is_file():
        try:
            return json.loads(f.read_text())
        except ValueError:
            pass
    c, g, length = _compute(str(path))
    res = {"bpm": round(c, 2), "beats": [round(t, 4) for t in g], "length": round(length, 4)}
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".part")
    tmp.write_text(json.dumps(res))
    tmp.replace(f)
    return res


def loop_beats(beats: list[float], length: float, start: float, total: float) -> list[float]:
    """Battements dans le temps de sortie : morceau bouclé (période `length`), lu à partir de `start`, sur `total` s."""
    if length <= 0 or not beats:
        return []
    out: list[float] = []
    k = 0
    while k * length - start < total:
        for b in beats:
            t = b + k * length - start
            if 0 <= t < total - 1e-9:
                out.append(t)
        k += 1
    return sorted(out)


def snap_durations(durs: list[float], beats_out: list[float], lo: float, eps: float = 1e-6) -> list[float]:
    """Raccourcit chaque scène jusqu'au dernier battement de [T+lo, T+d] (T = début cumulé en sortie).
    Jamais plus longue que d, jamais sous lo ; sans battement dans cette plage, la durée reste d."""
    b = np.asarray(sorted(beats_out))
    out: list[float] = []
    t = 0.0
    for d in durs:
        cand = b[(b >= t + lo - eps) & (b <= t + d + eps)] if len(b) else b
        e = d if len(cand) == 0 else min(d, float(cand.max()) - t)
        out.append(e)
        t += e
    return out
