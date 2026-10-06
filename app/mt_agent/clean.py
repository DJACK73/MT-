from __future__ import annotations
import os, shutil
from pathlib import Path

_DECOUPES = ("workspace/plans", "workspace/thumbs", "workspace/previews")
LEVELS: dict[int, tuple[str, ...]] = {
    1: _DECOUPES,
    2: (*_DECOUPES, "output"),
    3: (*_DECOUPES, "output", "inbox"),
}

def plan_clean(root: Path, level: int) -> list[Path]:
    """Entrées de 1er niveau qui seraient supprimées. Ignore les noms commençant par '.'."""
    if level not in LEVELS:
        raise ValueError(f"niveau inconnu: {level}")
    base = root.resolve()
    out: list[Path] = []
    for rel in LEVELS[level]:
        d = base / rel
        if d.is_dir() and not d.is_symlink():
            out += sorted(p for p in d.iterdir() if not p.name.startswith("."))
    return out

def size_of(p: Path) -> int:
    if p.is_symlink() or p.is_file():
        return p.lstat().st_size
    return sum(f.lstat().st_size for f in p.rglob("*") if f.is_file() and not f.is_symlink())

def run_clean(root: Path, level: int) -> tuple[int, list[str]]:
    """Supprime ce que plan_clean liste. Retourne (supprimées, erreurs). Niveau 3 refusé d'emblée si inbox est en lecture seule."""
    todo = plan_clean(root, level)
    if level == 3:
        inbox = root.resolve() / "inbox"
        if any(p.parent == inbox for p in todo) and not os.access(inbox, os.W_OK):
            raise PermissionError("inbox en lecture seule : rien n'a été supprimé")
    done, errors = 0, []
    for p in todo:
        try:
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)
            else:
                p.unlink()
            done += 1
        except OSError as e:
            errors.append(f"{p.name}: {e}")
    return done, errors
