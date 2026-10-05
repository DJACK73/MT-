from __future__ import annotations
from .approval import PlanError
from .models import Plan

def parse_selection(spec: str, n: int) -> set[int]:
    """'1-3,7' -> {1,2,3,7} (numéros à partir de 1). Toute erreur lève PlanError."""
    out: set[int] = set()
    for part in (p.strip() for p in spec.split(",")):
        lo_s, sep, hi_s = part.partition("-")
        try:
            lo = int(lo_s)
            hi = int(hi_s) if sep else lo
        except ValueError as e:
            raise PlanError(f"sélection invalide: {part!r}") from e
        if lo < 1 or hi > n or lo > hi:
            raise PlanError(f"hors limites 1..{n}: {part}")
        out.update(range(lo, hi + 1))
    return out

def select_scenes(plan: Plan, spec: str) -> Plan:
    """Nouveau plan en attente : seules les scènes listées sont sélectionnées. L'approbation est annulée."""
    if plan.status == "rendered":
        raise PlanError("plan déjà rendu")
    keep = parse_selection(spec, len(plan.scenes))
    scenes = [s.model_copy(update={"selected": (i + 1) in keep}) for i, s in enumerate(plan.scenes)]
    return plan.model_copy(update={"scenes": scenes, "status": "pending_human_review", "approved_hash": None})

def spec_from_flags(flags: list[bool]) -> str:
    """[T,F,T,T,T] -> '1,3-5' (numéros à partir de 1). Aucune case cochée -> ''."""
    out: list[str] = []
    i = 0
    while i < len(flags):
        if not flags[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(flags) and flags[j + 1]:
            j += 1
        out.append(str(i + 1) if i == j else f"{i + 1}-{j + 1}")
        i = j + 1
    return ",".join(out)
