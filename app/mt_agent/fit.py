from __future__ import annotations
import math

Span = tuple[float, float]


def split_long(spans: list[Span], min_s: float, max_s: float) -> list[Span]:
    if not 0 < min_s <= max_s:
        raise ValueError("0 < min_s <= max_s requis")
    out: list[Span] = []
    for a, b in spans:
        d = b - a
        n = max(1, math.ceil(d / max_s - 1e-9))
        if n > 1 and d / n < min_s:
            n = max(1, math.floor(d / min_s + 1e-9))
        step = d / n
        out += [(a + i * step, b if i == n - 1 else a + (i + 1) * step) for i in range(n)]
    return out


_EPS = 1e-9


def _feasible(r: float, min_s: float, max_s: float) -> bool:
    if r < min_s - _EPS:
        return False
    n = max(1, math.ceil(r / max_s - _EPS))
    return n * min_s <= r + _EPS


def fit_window(bounds: list[float], min_s: float, max_s: float) -> list[Span]:
    if not 0 < min_s <= max_s:
        raise ValueError("0 < min_s <= max_s requis")
    if len(bounds) < 2 or any(b <= a for a, b in zip(bounds, bounds[1:])):
        raise ValueError("bornes strictement croissantes, 2 minimum")
    end, s = bounds[-1], bounds[0]
    out: list[Span] = []
    while end - s > _EPS:
        r = end - s
        if r <= max_s + _EPS:
            out.append((s, end))
            break
        cands = [c for c in bounds
                 if min_s - _EPS <= c - s <= max_s + _EPS and _feasible(end - c, min_s, max_s)]
        if cands:
            e = max(cands)
        else:
            n = math.ceil(r / max_s - _EPS)
            if n * min_s > r + _EPS:
                n = max(1, math.floor(r / min_s + _EPS))
            e = end if n == 1 else s + r / n
        out.append((s, e))
        s = e
    return out
