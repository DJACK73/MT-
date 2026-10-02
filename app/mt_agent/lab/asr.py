from __future__ import annotations

def transcribe(path: str, model: str = "base", language: str | None = None) -> list[dict]:
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(path, language=language, vad_filter=True)
    return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
