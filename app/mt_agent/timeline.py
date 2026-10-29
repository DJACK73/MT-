from __future__ import annotations

import html

FRISE_CSS = (
    "<style>"
    ".fr-strip{display:flex;align-items:stretch;overflow-x:auto;padding:4px 0}"
    ".fr-s{flex:0 0 auto;position:relative;height:100%;background:#1e293b;border:1px solid #334155;border-radius:6px}"
    ".fr-s img{width:100%;height:100%;object-fit:cover;border-radius:5px;display:block}"
    ".fr-s span{position:absolute;left:0;right:0;bottom:0;font-size:11px;color:#fff;background:#0009;"
    "padding:1px 4px;white-space:nowrap;overflow:hidden;border-radius:0 0 5px 5px}"
    ".fr-j{flex:0 0 auto;width:20px;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:12px}"
    "</style>"
)


def frise_html(items: list[dict], px_per_s: float = 28.0, height: int = 96, min_w: int = 72) -> str:
    """Bande horizontale : une cellule par scène (largeur = durée), un repère « ▸ » entre deux scènes."""
    cells: list[str] = []
    for k, it in enumerate(items):
        w = max(min_w, round(float(it["dur"]) * px_per_s))
        img = f'<img src="{html.escape(it["uri"], quote=True)}">' if it.get("uri") else ""
        cells.append(f'<div class="fr-s" style="width:{w}px">{img}<span>{html.escape(str(it["label"]))}</span></div>')
        if k < len(items) - 1:
            cells.append('<div class="fr-j">▸</div>')
    return f'<div class="fr-strip" style="height:{height}px">' + "".join(cells) + "</div>"
