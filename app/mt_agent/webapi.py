from __future__ import annotations

import threading
from . import avtools
from .export import Look, export_clips, export_plan
from .clean import plan_clean, run_clean, size_of
from .preview import preview_clip
from pathlib import Path
from .approval import PlanError, approve, is_approved, plan_id, save_plan
from .avtools import extract_audio, remove_audio, stack_videos
from .cmd import scan_video
from .compose import letter
from .fit import window_flag
from .models import Options, Plan
from .paths import ensure_outside_inbox
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


_VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}  # = dashboard.VIDEO_EXT
_TOOLS = {"audio": (extract_audio, ".m4a"), "muet": (remove_audio, "-muet.mp4")}


def list_inbox(root: Path) -> list[str]:
    d = root / "inbox"
    if not d.is_dir():
        return []
    return sorted(x.name for x in d.iterdir() if x.is_file() and x.suffix.lower() in _VIDEO_EXT)


def run_tool(root: Path, name: str, tool: str) -> dict:
    if tool not in _TOOLS:
        raise ValueError(f"outil inconnu: {tool}")
    src = root / "inbox" / name
    if Path(name).name != name or src.suffix.lower() not in _VIDEO_EXT or not src.is_file():
        raise ValueError(f"vidéo invalide: {name}")
    fn, tail = _TOOLS[tool]
    out = ensure_outside_inbox(root / "output" / tool / (src.stem + tail), root)
    out.parent.mkdir(parents=True, exist_ok=True)
    fn(src, out)
    return {"out": f"{tool}/{out.name}", "tool": tool}


def run_stack(root: Path, names: list[str], mode: str, fit: str = "ajuster") -> dict:
    if not isinstance(names, list):
        raise ValueError("videos: liste attendue")
    if fit not in avtools.STACK_FITS:
        raise ValueError(f"cadrage inconnu: {fit}")
    if mode not in avtools.STACK_MODES:
        raise ValueError(f"disposition inconnue: {mode}")
    srcs = []
    for n in names:
        if not isinstance(n, str):
            raise ValueError(f"vidéo invalide: {n}")
        s = root / "inbox" / n
        if Path(n).name != n or s.suffix.lower() not in _VIDEO_EXT or not s.is_file():
            raise ValueError(f"vidéo invalide: {n}")
        srcs.append(s)
    tag = "-remplir" if fit == "remplir" and mode in avtools.FIT_MODES else ""
    base = "__".join(s.stem[:40] for s in srcs)
    out = ensure_outside_inbox(root / "output" / "collage" / f"{base}-{mode}{tag}.mp4", root)
    out.parent.mkdir(parents=True, exist_ok=True)
    stack_videos(srcs, out, mode, fit)
    return {"out": f"collage/{out.name}", "tool": "stack"}


def _plans(root: Path) -> list[tuple[Path, Plan]]:
    d = _dir(root)
    if not d.is_dir():
        return []
    out: list[tuple[Path, Plan]] = []
    for p in sorted((x for x in d.iterdir() if x.is_file() and x.suffix == ".json"),
                    key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            out.append((p, Plan.model_validate_json(p.read_text())))
        except (ValueError, OSError):
            continue
    return out


def list_videos(root: Path) -> list[dict]:
    cut = {Path(s.path).name for _, pl in _plans(root) for s in pl.sources}
    return [{"n": n, "cut": n in cut} for n in list_inbox(root)]


def run_cut(root: Path, name: str, threshold: float, min_s: float, max_s: float | None,
            framing: str = "blur_pad") -> dict:
    src = root / "inbox" / name
    if Path(name).name != name or src.suffix.lower() not in _VIDEO_EXT or not src.is_file():
        raise ValueError(f"vidéo invalide: {name}")
    if max_s is not None and max_s < min_s:
        raise ValueError("max doit être >= min")
    opt = Options(threshold=threshold, min_scene_seconds=min_s, max_scene_seconds=max_s, framing=framing)
    try:
        rel = str(src.resolve().relative_to(root.resolve()))
    except ValueError:
        rel = str(src.resolve())
    for p, pl in _plans(root):
        if len(pl.sources) == 1 and pl.sources[0].path == rel and pl.options == opt:
            return {"name": p.name, "reused": True, "scenes": len(pl.scenes)}
    plan = scan_video(src, root, opt)
    d = ensure_outside_inbox(_dir(root), root)
    d.mkdir(parents=True, exist_ok=True)
    return {"name": save_plan(plan, d).name, "reused": False, "scenes": len(plan.scenes)}


_JOB: dict = {"state": "idle"}
_LOCK = threading.Lock()
_THREAD: threading.Thread | None = None
_QUALITY = {"normal": 20, "haute": 16}


def get_job() -> dict:
    with _LOCK:
        return dict(_JOB)


def _rel(p: Path, root: Path) -> str:
    try:
        return str(Path(p).relative_to(root))
    except ValueError:
        return str(p)


def start_export(root: Path, name: str, kind: str, ratio: str, speed: float,
                 quality: str, audio: str, mirror: list | None = None) -> dict:
    global _THREAD
    if kind not in ("video", "clips"):
        raise ValueError(f"type d'export inconnu: {kind}")
    if ratio not in ("9:16", "16:9", "1:1"):
        raise ValueError(f"format inconnu: {ratio}")
    if audio not in ("none", "source"):
        raise ValueError(f"son inconnu: {audio}")
    if quality not in _QUALITY:
        raise ValueError(f"qualité inconnue: {quality}")
    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not 0.5 <= speed <= 2:
        raise ValueError("vitesse: nombre entre 0,5 et 2 attendu")
    mir = _mirror(mirror or [])
    plan = _load(root, name)
    mir = _mirror(mir, len(plan.scenes))
    with _LOCK:
        if _JOB.get("state") == "running":
            raise PlanError("un export est déjà en cours")
        _JOB.clear()
        _JOB.update(state="running", kind=kind, name=name)
    look = Look(ratio=ratio, speed=float(speed), audio=audio, mirror_only=mir)
    crf = _QUALITY[quality]

    def work() -> None:
        try:
            if kind == "video":
                mp4, _ = export_plan(plan, root, root / "output" / "assemble", crf=crf, look=look)
                outs = [mp4]
            else:
                outs = export_clips(plan, root, root / "output", crf=crf, look=look)
            res = {"state": "done", "files": [_rel(p, root) for p in outs]}
        except Exception as e:
            res = {"state": "error", "error": str(e)}
        with _LOCK:
            _JOB.clear()
            _JOB.update(res, kind=kind, name=name)

    _THREAD = threading.Thread(target=work, daemon=True)
    _THREAD.start()
    return {"started": True}


def _lvl(level: int) -> int:
    if isinstance(level, bool) or level not in (1, 2):
        raise ValueError("niveau 1 ou 2 attendu (inbox se vide dans l'Explorateur Windows)")
    return level


def clean_preview(root: Path, level: int) -> dict:
    todo = plan_clean(root, _lvl(level))
    return {"level": level, "count": len(todo), "bytes": sum(size_of(p) for p in todo)}


def do_clean(root: Path, level: int) -> dict:
    _lvl(level)
    if get_job().get("state") == "running":
        raise PlanError("un export est en cours : attends sa fin")
    done, errs = run_clean(root, level)
    return {"deleted": done, "errors": errs}


def _mirror(m, n: int | None = None) -> frozenset:
    if not isinstance(m, (list, tuple, set, frozenset)) or any(isinstance(x, bool) or not isinstance(x, int) for x in m):
        raise ValueError("miroir: liste de numéros de scène attendue")
    bad = sorted(x for x in m if n is not None and not 1 <= x <= n)
    if bad:
        raise ValueError(f"miroir: scènes inconnues {bad}")
    return frozenset(m)


def preview(root: Path, name: str, n: int, mirror: bool = False, speed: float = 1.0) -> Path:
    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not 0.5 <= speed <= 2:
        raise ValueError("vitesse: nombre entre 0,5 et 2 attendu")
    plan = _load(root, name)
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= len(plan.scenes):
        raise ValueError(f"scène inconnue: {n}")
    sc = plan.scenes[n - 1]
    src = next((s for s in plan.sources if s.id == sc.source_id), None)
    if src is None:
        raise PlanError(f"source absente pour la scène {n}")
    p = Path(src.path)
    return preview_clip(p if p.is_absolute() else root / p, sc.start, sc.end, root,
                        mirror=bool(mirror), speed=float(speed))
