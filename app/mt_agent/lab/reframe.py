from __future__ import annotations
import statistics
from pathlib import Path
from typing import Literal

Framing = Literal["pad", "crop_center", "blur_pad", "face_track"]

def _cascade() -> str:
    import cv2
    base = getattr(getattr(cv2, "data", None), "haarcascades", None) or str(Path(cv2.__file__).parent / "data") + "/"
    return base + "haarcascade_frontalface_default.xml"

def sample_faces(path: str, fps: float = 2.0) -> list[tuple[float, float | None]]:
    import cv2
    cap = cv2.VideoCapture(path)
    src = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, round(src / fps))
    det = cv2.CascadeClassifier(_cascade())
    if det.empty():
        raise RuntimeError("cascade Haar introuvable : " + _cascade())
    out: list[tuple[float, float | None]] = []
    i = 0
    while True:
        if i % step == 0:
            ok, frame = cap.read()
            if not ok:
                break
            g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = det.detectMultiScale(g, 1.1, 5, minSize=(60, 60))
            cx = None
            if len(faces):
                x, _, w, _ = max(faces, key=lambda f: f[2] * f[3])
                cx = (x + w / 2) / frame.shape[1]
            out.append((i / src, cx))
        elif not cap.grab():
            break
        i += 1
    cap.release()
    return out

def scene_center(samples: list[tuple[float, float | None]], a: float, b: float) -> float:
    xs = [c for t, c in samples if a <= t < b and c is not None]
    return statistics.median(xs) if xs else 0.5

def framing_filter(mode: Framing, src_w: int, src_h: int, cx: float = 0.5,
                   w: int = 1080, h: int = 1920) -> str:
    if mode == "pad":
        return (f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v]")
    if mode == "blur_pad":
        return (f"[0:v]split[a][b];"
                f"[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=20:5[bg];"
                f"[b]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[v]")
    cw = int(src_h * w / h) // 2 * 2
    center = 0.5 if mode == "crop_center" else cx
    x = max(0, min(src_w - cw, int(center * src_w - cw / 2)))
    return f"[0:v]crop={cw}:{src_h}:{x}:0,scale={w}:{h},setsar=1,format=yuv420p[v]"
