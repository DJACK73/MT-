from __future__ import annotations
import os
from collections.abc import Mapping
from pathlib import Path

def resolve_root(env: Mapping[str, str] = os.environ, default: Path | None = None) -> Path:
    """MT_HOME si défini, sinon la racine du projet. Même code en venv et en conteneur."""
    base = default if default is not None else Path(__file__).resolve().parents[2]
    return Path(env.get("MT_HOME", base)).resolve()

ROOT: Path = resolve_root()

def ensure_outside_inbox(p: Path, root: Path = ROOT) -> Path:
    """inbox/ en lecture seule : refuse inbox/ et tout chemin dessous (liens symboliques résolus)."""
    inbox = (root / "inbox").resolve()
    q = p.resolve()
    if q == inbox or inbox in q.parents:
        raise PermissionError(f"inbox/ en lecture seule: {p}")
    return p
