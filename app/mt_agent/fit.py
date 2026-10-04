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
