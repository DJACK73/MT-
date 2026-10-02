from __future__ import annotations
import subprocess, sys, wave
import numpy as np
from .beats import _pcm, flux, pick, bpm, grid_from_onsets, SR
from .ffx import duration

v, t0, dur = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
f = flux(_pcm(v))
c, beats = grid_from_onsets(pick(f), bpm(f), duration(v))
n = int(dur * SR)
click = np.zeros(n, np.float32)
m = int(0.03 * SR)
tick = (0.5 * np.sin(2 * np.pi * 1500 * np.arange(m) / SR) * np.hanning(m)).astype(np.float32)
for b in beats:
    i = int((b - t0) * SR)
    if 0 <= i < n - m:
        click[i:i + m] += tick
with wave.open("workspace/lab/clicks.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(click, -1, 1) * 32767).astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t0), "-t", str(dur), "-i", v,
                "-i", "workspace/lab/clicks.wav",
                "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "28", "-c:a", "aac", "workspace/lab/beats_check.mp4"], check=True)
print(f"bpm={c:.1f} -> workspace/lab/beats_check.mp4")
