"""Etalonnage et effets du dashboard : logique pure (sans Streamlit), testable aussi dans l'image."""
from __future__ import annotations

# Libelles des cases d'effets ; memes cles que export.FX (verifie par tests/test_grade.py).
FX_UI: dict[str, str] = {"bw": "Noir et blanc", "vignette": "Vignette", "blur": "Flou", "grain": "Grain"}
# Surcout de rendu ~ mesure (vignette +52 %, flou +44 %, grain x2).
FX_COST: dict[str, float] = {"vignette": 0.5, "blur": 0.5, "grain": 1.0}


def grade_kw(bright: int, contrast: int, sat: int, fx: list[str]) -> dict:
    """Pourcentages du GUI (luminosite -30..30, contraste 50..150, saturation 0..200) -> kwargs de Look ; defauts omis."""
    kw: dict = {}
    if bright != 0:
        kw["bright"] = bright / 100
    if contrast != 100:
        kw["contrast"] = contrast / 100
    if sat != 100:
        kw["sat"] = sat / 100
    if fx:
        kw["fx"] = frozenset(fx)
    return kw


def fx_cost(kw: dict) -> float:
    """Facteur de duree de rendu (>= 1) selon les effets actifs de kw."""
    return 1.0 + sum(FX_COST.get(n, 0.0) for n in kw.get("fx", ()))
