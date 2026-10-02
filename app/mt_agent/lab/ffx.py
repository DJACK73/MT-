from __future__ import annotations
import subprocess

def run_ffmpeg(args: list[str], timeout: int = 1800) -> str:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    return r.stderr

def duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())
