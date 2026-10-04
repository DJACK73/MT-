from __future__ import annotations
import argparse, sys
from pathlib import Path
from pydantic import ValidationError
from .approval import PlanError, approve, plan_id, save_plan
from .cuts import detect_cuts
from .export import export_plan
from .ffx import MediaError, duration
from .models import Options, Plan, Scene, Source
from .paths import ROOT, ensure_outside_inbox
from .scenes import merge_short

def scan_video(video: Path, root: Path, opt: Options, select_all: bool = True) -> Plan:
    if not video.is_file():
        raise PlanError(f"vidéo introuvable: {video}")
    total = duration(str(video))
    spans = merge_short(detect_cuts(str(video), opt.threshold), total, opt.min_scene_seconds)
    try:
        rel = str(video.resolve().relative_to(root.resolve()))
    except ValueError:
        rel = str(video.resolve())
    return Plan(options=opt, sources=[Source(id="s0", path=rel, duration=total)],
                scenes=[Scene(source_id="s0", start=a, end=b, selected=select_all) for a, b in spans])

def _load(p: str) -> Plan:
    return Plan.model_validate_json(Path(p).read_text())

def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(prog="mt")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="vidéo -> plan en attente de validation")
    s.add_argument("video")
    s.add_argument("--threshold", type=float, default=0.35)
    s.add_argument("--min-scene", type=float, default=1.0)
    s.add_argument("--framing", choices=["blur_pad", "crop_center"], default="blur_pad")
    s.add_argument("--profile", choices=["youtube", "vertical"], default="vertical")
    s.add_argument("--select", choices=["all", "none"], default="all")
    sub.add_parser("approve", help="plan en attente -> plan approuvé").add_argument("plan")
    sub.add_parser("export", help="rend un plan approuvé").add_argument("plan")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "scan":
            opt = Options(threshold=a.threshold, min_scene_seconds=a.min_scene, framing=a.framing, profile=a.profile)
            plan = scan_video(Path(a.video), root, opt, a.select == "all")
            out_dir = ensure_outside_inbox(root / "workspace" / "plans", root)
            print(save_plan(plan, out_dir))
            print(f"{len(plan.scenes)} scènes, {sum(x.selected for x in plan.scenes)} sélectionnées", file=sys.stderr)
        elif a.cmd == "approve":
            plan = _load(a.plan)
            print(save_plan(approve(plan), Path(a.plan).resolve().parent))
        else:
            mp4, done = export_plan(_load(a.plan), root, root / "output")
            print(mp4); print(done)
    except (PlanError, MediaError, PermissionError, ValidationError, OSError) as e:
        print(f"ERREUR: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
