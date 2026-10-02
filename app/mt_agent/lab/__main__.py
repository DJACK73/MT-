from __future__ import annotations
import argparse, json, time
from pathlib import Path
from .ffx import duration

def timed(fn):
    t = time.perf_counter(); r = fn(); return r, round(time.perf_counter() - t, 1)

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--only", default="silence,energy,scenes,faces,asr")
    a = p.parse_args()
    todo, v, rep = set(a.only.split(",")), a.video, {}
    total = duration(v)
    rep["duration_s"] = round(total, 1)
    if "silence" in todo:
        from .silence import detect_silences
        s, sec = timed(lambda: detect_silences(v))
        rep["silence"] = {"sec": sec, "count": len(s), "silent_total_s": round(sum(b - x for x, b in s), 1), "first": s[:3]}
    if "energy" in todo:
        from .energy import energy_profile, peaks
        e, sec = timed(lambda: energy_profile(v))
        rep["energy"] = {"sec": sec, "samples": len(e), "peaks": peaks(e) if e else "AUCUN ECHANTILLON: parsing ebur128 a corriger"}
    if "scenes" in todo:
        from .scenes import detect_cuts, to_scenes
        grid = {}
        for th in (0.2, 0.35, 0.5):
            cuts, sec = timed(lambda: detect_cuts(v, th))
            for ms in (0.0, 1.0, 1.5):
                grid[f"thr={th} min={ms}"] = len(to_scenes(cuts, total, ms))
            grid[f"thr={th} sec"] = sec
        rep["scenes"] = grid
    if "faces" in todo:
        from .reframe import sample_faces, scene_center
        f, sec = timed(lambda: sample_faces(v))
        hit = [c for _, c in f if c is not None]
        rep["faces"] = {"sec": sec, "samples": len(f), "with_face_pct": round(100 * len(hit) / max(1, len(f)), 1),
                        "center_x_median": scene_center(f, 0, total)}
    if "asr" in todo:
        from .asr import transcribe
        t, sec = timed(lambda: transcribe(v))
        rep["asr"] = {"sec": sec, "segments": len(t), "first": t[:3]}
    out = Path("workspace/lab"); out.mkdir(parents=True, exist_ok=True)
    (out / f"{Path(v).stem}.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False))
    print(json.dumps(rep, indent=2, ensure_ascii=False))

main()
