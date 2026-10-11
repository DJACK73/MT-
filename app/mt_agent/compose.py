from __future__ import annotations
from .approval import PlanError
from .models import Options, Plan, Scene, Source


def letter(i: int) -> str:
    """0 -> 'A', 25 -> 'Z', 26 -> 'AA'."""
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def compose_plan(plans: list[Plan], order: list[tuple[int, int]]) -> Plan:
    """Un plan en attente : les scènes (index du plan, n° de scène base 1) dans CET ordre.
    Sources renumérotées s0, s1… dans l'ordre des plans ; même fichier = même source."""
    if not plans:
        raise PlanError("aucun plan à composer")
    if not order:
        raise PlanError("aucune scène choisie")
    if len(set(order)) != len(order):
        raise PlanError("scène choisie deux fois")
    picked: list[tuple[int, Scene]] = []
    for pi, n in order:
        if not 0 <= pi < len(plans):
            raise PlanError(f"plan inconnu: {pi}")
        pl = plans[pi]
        if not 1 <= n <= len(pl.scenes):
            raise PlanError(f"scène hors limites 1..{len(pl.scenes)}: {n}")
        sc = pl.scenes[n - 1]
        if sc.source_id not in {s.id for s in pl.sources}:
            raise PlanError(f"source inconnue: {sc.source_id}")
        picked.append((pi, sc))
    sources: list[Source] = []
    by_key: dict[tuple[str, float, float], str] = {}
    new_id: dict[tuple[int, str], str] = {}
    for pi in sorted({p for p, _ in picked}):
        need = {sc.source_id for p, sc in picked if p == pi}
        for src in plans[pi].sources:
            if src.id not in need:
                continue
            key = (src.path, src.duration, src.offset_seconds)
            if key not in by_key:
                by_key[key] = f"s{len(sources)}"
                sources.append(src.model_copy(update={"id": by_key[key]}))
            new_id[(pi, src.id)] = by_key[key]
    scenes = [sc.model_copy(update={"source_id": new_id[(pi, sc.source_id)], "selected": True}) for pi, sc in picked]
    opts = [plans[pi].options for pi in sorted({p for p, _ in picked})]
    mx = None if any(o.max_scene_seconds is None for o in opts) else max(o.max_scene_seconds for o in opts)
    options = opts[0].model_copy(update={"min_scene_seconds": min(o.min_scene_seconds for o in opts),
                                         "max_scene_seconds": mx})
    return Plan(options=options, sources=sources, scenes=scenes)
