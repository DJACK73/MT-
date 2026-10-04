from __future__ import annotations

Span = tuple[float, float]

def merge_short(cuts: list[float], total: float, min_s: float, eps: float = 1e-9) -> list[Span]:
    """Découpe [0,total] aux coupes, fusionne toute scène < min_s avec sa voisine. Contigu, ordonné."""
    if total <= 0 or min_s < 0:
        raise ValueError("total > 0 et min_s >= 0 requis")
    pts = [0.0, *sorted({c for c in cuts if 0 < c < total}), total]
    out: list[list[float]] = []
    for a, b in zip(pts, pts[1:]):
        if out and b - a < min_s - eps:
            out[-1][1] = b
        else:
            out.append([a, b])
    if len(out) > 1 and out[0][1] - out[0][0] < min_s - eps:
        out[1][0] = out[0][0]
        out.pop(0)
    return [(a, b) for a, b in out]
