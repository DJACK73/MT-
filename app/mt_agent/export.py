from __future__ import annotations
from collections.abc import Callable
from pathlib import Path
from .approval import PlanError, assert_renderable, plan_id, save_plan
from .ffx import run_ffmpeg
from .models import Plan
from .paths import ensure_outside_inbox

PROFILES: dict[str, tuple[int, int]] = {"youtube": (1920, 1080), "vertical": (1080, 1920)}
_TAIL = "setsar=1,fps=25,format=yuv420p"

def _node(i: int, j: int, s: float, e: float, framing: str, w: int, h: int) -> str:
    head = f"[{j}:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS"
    fill = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    if framing == "crop_center":
        return f"{head},{fill},{_TAIL}[v{i}]"
    sw, sh = w // 10, h // 10  # flou calculé à 1/10 de la taille, puis agrandi (4,6x plus rapide, mesuré)
    return (f"{head}[t{i}];[t{i}]split[a{i}][b{i}];"
            f"[a{i}]scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},"
            f"boxblur=2:1,scale={w}:{h}[bg{i}];"
            f"[b{i}]scale={w}:{h}:force_original_aspect_ratio=decrease[fg{i}];"
            f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2,{_TAIL}[v{i}]")

def build_graph(plan: Plan) -> tuple[list[str], str]:
    """Retourne (chemins sources dans l'ordre des entrées, filter_complex). Vidéo seule."""
    chosen = [s for s in plan.scenes if s.selected]
    if not chosen:
        raise PlanError("aucune scène sélectionnée")
    paths = {s.id: s.path for s in plan.sources}
    order: list[str] = []
    for sc in chosen:
        if sc.source_id not in paths:
            raise PlanError(f"source inconnue: {sc.source_id}")
        if sc.source_id not in order:
            order.append(sc.source_id)
    w, h = PROFILES[plan.options.profile]
    nodes = [_node(i, order.index(sc.source_id), sc.start, sc.end, plan.options.framing, w, h)
             for i, sc in enumerate(chosen)]
    labels = "".join(f"[v{i}]" for i in range(len(chosen)))
    return [paths[k] for k in order], ";".join([*nodes, f"{labels}concat=n={len(chosen)}:v=1:a=0[out]"])

def export_plan(plan: Plan, root: Path, out_dir: Path, crf: int = 20) -> tuple[Path, Path]:
    """Rend un plan approuvé. Retourne (mp4, json du plan rendu). Ne remplace jamais rien."""
    assert_renderable(plan)
    ensure_outside_inbox(out_dir, root)
    rels, fc = build_graph(plan)
    srcs = [Path(r) if Path(r).is_absolute() else root / r for r in rels]
    missing = [str(p) for p in srcs if not p.is_file()]
    if missing:
        raise PlanError(f"sources absentes: {missing}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{plan_id(plan)}.mp4"
    args: list[str] = []
    for p in srcs:
        args += ["-i", str(p)]
    args += ["-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-crf", str(crf),
             "-preset", "veryfast", "-movflags", "+faststart"]
    run_ffmpeg(args, out)
    done = save_plan(plan.model_copy(update={"status": "rendered"}), out_dir)
    return out, done

def export_clips(plan: Plan, root: Path, out_dir: Path, crf: int = 20,
                 on_progress: Callable[[int, int], None] | None = None) -> list[Path]:
    """Un mp4 par scène sélectionnée, non collés : out_dir/clips/<source>-<plan_id[:8]>/NNN.mp4.
    NNN = numéro (base 1) de la scène dans le plan. Ne remplace rien, ne change pas le statut.
    En cas d'échec au milieu, les clips déjà écrits restent."""
    assert_renderable(plan)
    ensure_outside_inbox(out_dir, root)
    chosen = [(n, sc) for n, sc in enumerate(plan.scenes, 1) if sc.selected]
    if not chosen:
        raise PlanError("aucune scène sélectionnée")
    paths = {s.id: s.path for s in plan.sources}
    srcs: dict[str, Path] = {}
    for _, sc in chosen:
        if sc.source_id not in paths:
            raise PlanError(f"source inconnue: {sc.source_id}")
        p = Path(paths[sc.source_id])
        srcs[sc.source_id] = p if p.is_absolute() else root / p
    missing = [str(p) for p in srcs.values() if not p.is_file()]
    if missing:
        raise PlanError(f"sources absentes: {missing}")
    w, h = PROFILES[plan.options.profile]
    stem = Path(paths[chosen[0][1].source_id]).stem
    folder = out_dir / "clips" / f"{stem}-{plan_id(plan)[:8]}"
    try:
        folder.mkdir(parents=True, exist_ok=False)
    except FileExistsError as e:
        raise PlanError(f"dossier déjà présent: {folder}") from e
    done: list[Path] = []
    for k, (n, sc) in enumerate(chosen, 1):
        d = sc.end - sc.start
        node = _node(0, 0, 0.0, d, plan.options.framing, w, h)
        args = ["-ss", f"{sc.start:.3f}", "-t", f"{d:.3f}", "-i", str(srcs[sc.source_id]),
                "-filter_complex", node, "-map", "[v0]", "-c:v", "libx264", "-crf", str(crf),
                "-preset", "veryfast", "-movflags", "+faststart"]
        dest = folder / f"{n:03d}.mp4"
        run_ffmpeg(args, dest)
        done.append(dest)
        if on_progress is not None:
            on_progress(k, len(chosen))
    return done
