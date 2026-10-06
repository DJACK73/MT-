from __future__ import annotations
import hashlib, json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Source(Strict):
    id: str
    path: str
    duration: float = Field(gt=0)
    offset_seconds: float = 0.0

class Scene(Strict):
    source_id: str
    start: float = Field(ge=0)
    end: float
    score: float = 0.0
    selected: bool = False

    @model_validator(mode="after")
    def _ordered(self) -> "Scene":
        if self.end <= self.start:
            raise ValueError("end doit être > start")
        return self

class Options(Strict):
    threshold: float = 0.35
    min_scene_seconds: float = 1.0
    framing: Literal["blur_pad", "crop_center"] = "blur_pad"
    profile: Literal["youtube", "vertical"] = "vertical"
    max_scene_seconds: float | None = Field(default=None, gt=0)

class Plan(Strict):
    version: Literal[2] = 2
    status: Literal["pending_human_review", "approved", "rendered"] = "pending_human_review"
    options: Options = Field(default_factory=Options)
    sources: list[Source]
    scenes: list[Scene]
    approved_hash: str | None = None

    def content_hash(self) -> str:
        d = self.model_dump(mode="json", exclude={"approved_hash", "status"})
        if d["options"].get("max_scene_seconds") is None:
            d["options"].pop("max_scene_seconds", None)
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
