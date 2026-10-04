from __future__ import annotations
import subprocess
from pathlib import Path

class MediaError(RuntimeError):
    pass

def run_ffmpeg(args: list[str], out: Path | None = None, fmt: str = "mp4", timeout: int = 1800) -> str:
    """out=None : sortie dans args (ex. `-f null -`). Sinon : refus d'écraser, écriture .part, rename."""
    part: Path | None = None
    tail: list[str] = []
    if out is not None:
        if out.exists():
            raise MediaError(f"refus d'écraser: {out}")
        part = out.with_name(out.name + ".part")
        part.unlink(missing_ok=True)
        tail = ["-f", fmt, str(part)]
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-nostdin", "-n", *args, *tail]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise MediaError("ffmpeg introuvable") from e
    except subprocess.TimeoutExpired as e:
        if part:
            part.unlink(missing_ok=True)
        raise MediaError(f"ffmpeg timeout après {timeout}s") from e
    if r.returncode or (part is not None and not part.exists()):
        if part:
            part.unlink(missing_ok=True)
        raise MediaError(r.stderr[-2000:])
    if part is not None:
        part.rename(out)
    return r.stderr

def duration(path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise MediaError(f"ffprobe indisponible : {e}") from e
    if r.returncode:
        raise MediaError(r.stderr[-500:])
    try:
        d = float(r.stdout.strip())
    except ValueError as e:
        raise MediaError(f"durée illisible : {r.stdout!r}") from e
    if d <= 0:
        raise MediaError(f"durée invalide : {d}")
    return d
