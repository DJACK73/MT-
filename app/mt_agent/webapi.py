from __future__ import annotations
from pathlib import Path
from .approval import PlanError, approve, is_approved, plan_id, save_plan
from .compose import letter
from .fit import window_flag
from .models import Plan
from .selection import select_scenes
from .thumbs import make_thumbnails


def _dir(root: Path) -> Path:
    return root / "workspace" / "plans"


def _path(root: Path, name: str) -> Path:
    if Path(name).name != name or not name.endswith(".json"):
        raise PlanError(f"nom de plan invalide: {name!r}")
    p = _dir(root) / name
    if not p.is_file():
        raise PlanError(f"plan introuvable: {name}")
    return p


def _load(root: Path, name: str) -> Plan:
    return Plan.model_validate_json(_path(root, name).read_text())


def _save_or_open(new: Plan, d: Path) -> Path:
    target = d / f"{plan_id(new)}.{new.status}.json"
    return target if target.exists() else save_plan(new, d)


def list_plans(root: Path) -> list[dict]:
    d = _dir(root)
    if not d.is_dir():
        return []
    files = sorted((x for x in d.iterdir() if x.is_file() and x.suffix == ".json"),
                   key=lambda x: x.stat().st_mtime, reverse=True)
    out: list[dict] = []
    for p in files:
        try:
            pl = Plan.model_validate_json(p.read_text())
        except (ValueError, OSError):
            continue
        out.append({"name": p.name, "status": pl.status, "sources": [Path(s.path).stem for s in pl.sources],
                    "selected": sum(s.selected for s in pl.scenes), "total": len(pl.scenes)})
    return out


def get_plan(root: Path, name: str) -> dict:
    plan = _load(root, name)
    lo = plan.options.min_scene_seconds
    mx = plan.options.max_scene_seconds
    hi = float("inf") if mx is None else mx
    ids = [s.id for s in plan.sources]
    rank = {n: r for r, (n, _) in enumerate(plan.chosen(), 1)}
    scenes = []
    for i, sc in enumerate(plan.scenes, 1):
        dur = sc.end - sc.start
        scenes.append({"n": i, "duration": round(dur, 3), "selected": sc.selected, "rank": rank.get(i),
                       "flag": window_flag(dur, lo, hi),
                       "source": letter(ids.index(sc.source_id)) if len(ids) > 1 and sc.source_id in ids else None})
    return {"name": name, "status": plan.status, "approved": is_approved(plan),
            "order": [n for n, _ in plan.chosen()],
            "kept_seconds": round(sum(s.end - s.start for _, s in plan.chosen()), 3), "scenes": scenes}


def apply_selection(root: Path, name: str, order: list[int]) -> dict:
    plan = _load(root, name)
    if not order:
        raise PlanError("aucune scène cochée")
    new = select_scenes(plan, ",".join(map(str, order)))
    if new.content_hash() == plan.content_hash():
        return {"name": name, "changed": False}
    return {"name": _save_or_open(new, _dir(root)).name, "changed": True}


def approve_plan(root: Path, name: str) -> dict:
    return {"name": _save_or_open(approve(_load(root, name)), _dir(root)).name}


def thumbnail(root: Path, name: str, n: int) -> Path | None:
    plan = _load(root, name)
    if not 1 <= n <= len(plan.scenes):
        raise PlanError(f"scène hors limites: {n}")
    return make_thumbnails(plan, root)[n - 1]
