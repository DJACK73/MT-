from .config import ROOT, cfg
from pathlib import Path
import json
import subprocess


def run(command, log):
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        with log.open("a") as stream:
            stream.write("\n$ " + " ".join(command) + "\n" + result.stderr)
        raise RuntimeError(f"FFmpeg failed; see {log}")


def render(plan_path):
    plan_file = Path(plan_path)
    plan = json.loads(plan_file.read_text())
    if plan["status"] != "approved" or not plan["human_validation"].get("approved"):
        raise ValueError("Validation humaine obligatoire avant rendu.")
    selected = [scene for scene in plan["scenes"] if scene.get("selected")]
    if not selected:
        raise ValueError("Aucune scène sélectionnée.")
    for export in plan["exports"]:
        existing = ROOT / export["output"]
        if existing.exists():
            raise FileExistsError(f"Export existant protégé : {existing}")

    source = plan["source"]["path"]
    work = ROOT / "workspace" / plan["plan_id"] / "renders"
    work.mkdir(parents=True, exist_ok=True)
    log = work / "render.log"
    log.touch(exist_ok=True)

    for export in plan["exports"]:
        profile = cfg()["profiles"][export["profile"]]
        profile_dir = work / export["profile"]
        profile_dir.mkdir(exist_ok=True)
        clips = []
        for index, scene in enumerate(selected, 1):
            clip = profile_dir / f"{index:03}.mp4"
            duration = scene["end_seconds"] - scene["start_seconds"]
            vf = (
                f"scale={profile['width']}:{profile['height']}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={profile['width']}:{profile['height']}:(ow-iw)/2:(oh-ih)/2,"
                "setsar=1,format=yuv420p"
            )
            if not clip.exists() or clip.stat().st_size == 0:
                run([
                    "ffmpeg", "-y", "-ss", str(scene["start_seconds"]),
                    "-t", str(duration), "-i", source, "-map", "0:v:0",
                    "-map", "0:a?", "-vf", vf, "-c:v", "libx264",
                    "-preset", "ultrafast", "-c:a", "aac", "-ar", "48000",
                    str(clip),
                ], log)
            clips.append(clip)

        manifest = profile_dir / "concat.txt"
        manifest.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips))
        output = ROOT / export["output"]
        output.parent.mkdir(parents=True, exist_ok=True)

        temporary = output.with_suffix(".part.mp4")
        try:
            run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
                "-c", "copy", "-movflags", "+faststart", str(temporary),
            ], log)
            run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1", str(temporary),
            ], log)
            temporary.replace(output)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        export["status"] = "rendered"

    plan["status"] = "rendered"
    plan_file.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")


