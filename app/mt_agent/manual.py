from __future__ import annotations
import re
from pathlib import Path

from .approval import PlanError
from .ffx import duration
from .models import Options, Plan, Scene, Source

_NUM = re.compile(r"^\d+(\.\d+)?$")
_SEP = re.compile(r"\s*[-–→]\s*")
_LINES = re.compile(r"[\n;]+|\s*,\s+|\s+,\s*")  # virgule séparatrice seulement si espacée : « 12,5 » reste un décimal


def parse_time(tok: str, total: float) -> float:
    """« 12.5 », « 12,5 », « 1:02.5 », « 1:02:03 » ou « fin » -> secondes."""
    t = tok.strip().lower().replace(",", ".")
    if t in ("fin", "end"):
        return total
    parts = t.split(":")
    if not 1 <= len(parts) <= 3 or not all(_NUM.match(p) for p in parts):
        raise ValueError(f"temps illisible: {tok!r}")
    sec = 0.0
    for p in parts:
        sec = sec * 60 + float(p)
    return sec


def parse_spans(text: str, total: float) -> list[tuple[float, float]]:
    """Une plage « début-fin » par ligne (ou séparées par « ; »). L'ordre saisi est conservé."""
    spans: list[tuple[float, float]] = []
    for raw in _LINES.split(text):
        line = raw.strip()
        if not line:
            continue
        bits = _SEP.split(line, maxsplit=1)
        if len(bits) != 2 or not bits[0] or not bits[1]:
            raise ValueError(f"plage illisible: {line!r} (attendu début-fin, ex. 12.5-16)")
        a, b = parse_time(bits[0], total), parse_time(bits[1], total)
        if b <= a:
            raise ValueError(f"fin <= début: {line!r}")
        if b > total + 1e-6:
            raise ValueError(f"hors vidéo ({total:.2f} s): {line!r}")
        spans.append((round(a, 3), round(min(b, total), 3)))
    if not spans:
        raise ValueError("aucune plage saisie")
    return spans


def whole_spans(total: float) -> list[tuple[float, float]]:
    return [(0.0, round(total, 3))]


def plan_from_spans(rel_path: str, total: float, spans: list[tuple[float, float]],
                    select_all: bool = True) -> Plan:
    return Plan(options=Options(min_scene_seconds=0.1),
                sources=[Source(id="s0", path=rel_path, duration=total)],
                scenes=[Scene(source_id="s0", start=a, end=b, selected=select_all) for a, b in spans])


def manual_plan(video: Path, root: Path, text: str | None, select_all: bool = True) -> Plan:
    """text=None -> vidéo entière (mode « Aucune »). Sinon plages saisies à la main."""
    if not video.is_file():
        raise PlanError(f"vidéo introuvable: {video}")
    total = duration(str(video))
    spans = whole_spans(total) if text is None else parse_spans(text, total)
    try:
        rel = str(video.resolve().relative_to(root.resolve()))
    except ValueError:
        rel = str(video.resolve())
    return plan_from_spans(rel, total, spans, select_all)
