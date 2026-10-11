from __future__ import annotations
from collections.abc import Callable
from pathlib import Path
from .approval import PlanError, assert_renderable, plan_id, save_plan
from .ffx import duration, has_audio, run_ffmpeg
from .models import Plan
from dataclasses import dataclass
from typing import Literal

from .paths import ensure_outside_inbox

PROFILES: dict[str, tuple[int, int]] = {"youtube": (1920, 1080), "vertical": (1080, 1920)}
_TAIL = "setsar=1,fps=25,format=yuv420p"


@dataclass(frozen=True)
class Look:
    """Rendu choisi à l'export : hors plan, donc hors hash et sans ré-approbation."""
    fit: Literal["bars", "fill", "none"] | None = None  # None = suit plan.options.framing
    background: Literal["blur", "black"] = "blur"  # fond des bandes (fit="bars")
    anchor: float = 0.5  # fit="fill" : 0 = bord gauche, 1 = bord droit
    audio: Literal["none", "source", "music", "mix"] = "none"  # son du clip ; défaut : muet
    audio_db: float = 0.0  # gain appliqué à l'audio de la source
    music: str | None = None  # fichier (relatif à la racine) pour audio="music" ou "mix"
    music_start: float = 0.0  # début dans le morceau (s)
    music_db: float = 0.0
    music_fade: float = 0.3  # fondu d'entrée et de sortie (s), 0..0.5


def _look(plan: Plan, look: Look | None) -> tuple[str, str, float]:
    look = look or Look()
    if not 0.0 <= look.anchor <= 1.0:
        raise PlanError(f"position hors de 0..1: {look.anchor}")
    fit = look.fit or ("fill" if plan.options.framing == "crop_center" else "bars")
    if fit == "none":  # source telle quelle
        return "none", look.background, look.anchor
    return ("crop_center" if fit == "fill" else "blur_pad"), look.background, look.anchor

_FADE = 0.02  # fondu de bord (s) : évite les clics aux coupes


def _audio(look: Look | None) -> tuple[bool, float]:
    """(audio de la source ?, gain en dB). Défaut : sans audio."""
    look = look or Look()
    if look.audio not in ("none", "source", "music", "mix"):
        raise PlanError(f"mode audio inconnu: {look.audio}")
    if not -40.0 <= look.audio_db <= 12.0:
        raise PlanError(f"volume hors de -40..+12 dB: {look.audio_db}")
    return look.audio in ("source", "mix"), look.audio_db


def _music(look: Look | None) -> tuple[bool, str, float, float, float]:
    """(musique ?, fichier, début s, gain dB, fondu s). Validé sans toucher au disque."""
    look = look or Look()
    if look.audio not in ("music", "mix"):
        return False, "", 0.0, 0.0, 0.0
    if not look.music:
        raise PlanError("mode musique : aucun fichier choisi")
    if look.music_start < 0:
        raise PlanError(f"début de la musique négatif: {look.music_start}")
    if not -40.0 <= look.music_db <= 12.0:
        raise PlanError(f"volume de la musique hors de -40..+12 dB: {look.music_db}")
    if not 0.0 <= look.music_fade <= 0.5:
        raise PlanError(f"fondu de la musique hors de 0..0.5 s: {look.music_fade}")
    return True, look.music, look.music_start, look.music_db, look.music_fade


def _check_music(p: Path, start: float) -> None:
    if not p.is_file():
        raise PlanError(f"musique absente: {p}")
    if start >= duration(str(p)):
        raise PlanError(f"début de la musique ({start:g} s) au-delà de sa durée")


def _mchain(idx: int, total: float, start: float, db: float, fade: float, out: str) -> str:
    """Entrée idx (bouclée par -stream_loop) coupée net à `total` s, gain, fondus."""
    f = min(fade, total / 2)
    parts = [f"atrim=start={start:.3f}:end={start + total:.3f}", "asetpts=PTS-STARTPTS",
             "aformat=sample_rates=48000:channel_layouts=stereo"]
    if db:
        parts.append(f"volume={db:g}dB")
    if f:
        parts += [f"afade=t=in:d={f:g}", f"afade=t=out:st={total - f:.3f}:d={f:g}"]
    return f"[{idx}:a]" + ",".join(parts) + f"[{out}]"


def _duck(src: str, mus: str, out: str) -> str:
    """Musique sous le son de la source (sidechain), puis mixage."""
    return (f"[{src}]asplit[{src}1][{src}2];"
            f"[{mus}][{src}1]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=300[{out}d];"
            f"[{out}d][{src}2]amix=inputs=2:duration=first:normalize=0[{out}]")


def _afilter(d: float, db: float = 0.0) -> str:
    f = min(_FADE, d / 2)
    vol = f"volume={db:g}dB," if db else ""
    return f"{vol}afade=t=in:d={f:g},afade=t=out:st={d - f:.3f}:d={f:g}"


def _anode(i: int, j: int, s: float, e: float) -> str:
    return (f"[{j}:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS,"
            f"aformat=sample_rates=48000:channel_layouts=stereo,{_afilter(e - s)}[a{i}]")


def _node(i: int, j: int, s: float, e: float, framing: str, w: int, h: int,
          bg: str = "blur", cx: float = 0.5) -> str:
    head = f"[{j}:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS"
    if framing == "none":  # trim seul : ni scale, ni pad, ni flou, ni fps
        return f"{head},format=yuv420p[v{i}]"
    pos = "" if cx == 0.5 else f":(iw-ow)*{cx:.3f}:(ih-oh)/2"
    fill = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}{pos}"
    if framing == "crop_center":
        return f"{head},{fill},{_TAIL}[v{i}]"
    if bg == "black":
        return (f"{head},scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,{_TAIL}[v{i}]")
    sw, sh = w // 10, h // 10  # flou calculé à 1/10 de la taille, puis agrandi (4,6x plus rapide, mesuré)
    return (f"{head}[t{i}];[t{i}]split[a{i}][b{i}];"
            f"[a{i}]scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh},"
            f"boxblur=2:1,scale={w}:{h}[bg{i}];"
            f"[b{i}]scale={w}:{h}:force_original_aspect_ratio=decrease[fg{i}];"
            f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2,{_TAIL}[v{i}]")

def build_graph(plan: Plan, look: Look | None = None) -> tuple[list[str], str]:
    """Retourne (chemins sources dans l'ordre des entrées, filter_complex). Vidéo seule."""
    chosen = [s for s in plan.scenes if s.selected]
    if not chosen:
        raise PlanError("aucune scène sélectionnée")
    paths = {s.id: s.path for s in plan.sources}
    order: list[str] = []
    for sc in chosen:
        if sc.source_id not in paths:
            raise PlanError(f"source inconnue: {sc.source_id}")
        if sc.source_id not in order:
            order.append(sc.source_id)
    w, h = PROFILES[plan.options.profile]
    fr, bg, cx = _look(plan, look)
    if fr == "none" and len(order) > 1:
        raise PlanError("cadrage « Aucun » : export assemblé limité à une seule source "
                        "(tailles possiblement différentes) ; utiliser les clips séparés")
    nodes = [_node(i, order.index(sc.source_id), sc.start, sc.end, fr, w, h, bg, cx)
             for i, sc in enumerate(chosen)]
    with_a, db = _audio(look)
    use_m, mpath, mstart, mdb, mfade = _music(look)
    n = len(chosen)
    srcs = [paths[k] for k in order]
    total = sum(sc.end - sc.start for sc in chosen)
    mix = with_a and use_m
    if not with_a:
        labels = "".join(f"[v{i}]" for i in range(n))
        parts = [*nodes, f"{labels}concat=n={n}:v=1:a=0[out]"]
    else:
        anodes = [_anode(i, order.index(sc.source_id), sc.start, sc.end) for i, sc in enumerate(chosen)]
        labels = "".join(f"[v{i}][a{i}]" for i in range(n))
        gain = f"volume={db:g}dB" if db else "anull"
        parts = [*nodes, *anodes, f"{labels}concat=n={n}:v=1:a=1[out][ac]",
                 f"[ac]{gain}[{'src' if mix else 'aud'}]"]
    if use_m:
        parts.append(_mchain(len(srcs), total, mstart, mdb, mfade, "mus" if mix else "aud"))
        if mix:
            parts.append(_duck("src", "mus", "aud"))
        srcs.append(mpath)  # la musique est la dernière entrée
    return srcs, ";".join(parts)

def export_plan(plan: Plan, root: Path, out_dir: Path, crf: int = 20,
                look: Look | None = None) -> tuple[Path, Path]:
    """Rend un plan approuvé. Retourne (mp4, json du plan rendu). Ne remplace jamais rien."""
    assert_renderable(plan)
    ensure_outside_inbox(out_dir, root)
    rels, fc = build_graph(plan, look)
    srcs = [Path(r) if Path(r).is_absolute() else root / r for r in rels]
    missing = [str(p) for p in srcs if not p.is_file()]
    if missing:
        raise PlanError(f"sources absentes: {missing}")
    with_a, _ = _audio(look)
    use_m, _, mstart, _, _ = _music(look)
    total = sum(sc.end - sc.start for sc in plan.scenes if sc.selected)
    vsrcs = srcs[:-1] if use_m else srcs
    if use_m:
        _check_music(srcs[-1], mstart)
    if with_a:
        silent = [str(p) for p in vsrcs if not has_audio(str(p))]
        if silent:
            raise PlanError(f"audio de la source : pas de piste audio dans {silent} ; choisir « Sans audio »")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{plan_id(plan)}.mp4"
    args: list[str] = []
    for p in vsrcs:
        args += ["-i", str(p)]
    if use_m:
        args += ["-stream_loop", "-1", "-i", str(srcs[-1])]
    args += ["-filter_complex", fc, "-map", "[out]"]
    if with_a or use_m:
        args += ["-map", "[aud]", "-c:a", "aac", "-b:a", "192k"]
    if use_m:
        args += ["-t", f"{total:.3f}"]
    args += ["-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-movflags", "+faststart"]
    run_ffmpeg(args, out)
    done = save_plan(plan.model_copy(update={"status": "rendered"}), out_dir)
    return out, done

def export_clips(plan: Plan, root: Path, out_dir: Path, crf: int = 20,
                 on_progress: Callable[[int, int], None] | None = None,
                 look: Look | None = None) -> list[Path]:
    """Un mp4 par scène sélectionnée, non collés : out_dir/clips/<source>-<plan_id[:8]>/NNN.mp4.
    NNN = numéro (base 1) de la scène dans le plan. Ne remplace rien, ne change pas le statut.
    En cas d'échec au milieu, les clips déjà écrits restent."""
    assert_renderable(plan)
    ensure_outside_inbox(out_dir, root)
    chosen = [(n, sc) for n, sc in enumerate(plan.scenes, 1) if sc.selected]
    if not chosen:
        raise PlanError("aucune scène sélectionnée")
    paths = {s.id: s.path for s in plan.sources}
    srcs: dict[str, Path] = {}
    for _, sc in chosen:
        if sc.source_id not in paths:
            raise PlanError(f"source inconnue: {sc.source_id}")
        p = Path(paths[sc.source_id])
        srcs[sc.source_id] = p if p.is_absolute() else root / p
    missing = [str(p) for p in srcs.values() if not p.is_file()]
    if missing:
        raise PlanError(f"sources absentes: {missing}")
    w, h = PROFILES[plan.options.profile]
    fr, bg, cx = _look(plan, look)
    with_a, db = _audio(look)
    use_m, mpath, mstart, mdb, mfade = _music(look)
    mfile = Path(mpath) if Path(mpath).is_absolute() else root / mpath
    sound: dict[str, bool] = {}
    if use_m:
        _check_music(mfile, mstart)
    stem = Path(paths[chosen[0][1].source_id]).stem
    base = f"{stem}-{plan_id(plan)[:8]}"
    folder = out_dir / "clips" / base
    for k in range(1, 100):  # dossier déjà présent : suffixe -2, -3… (rien n'est écrasé)
        folder = out_dir / "clips" / (base if k == 1 else f"{base}-{k}")
        try:
            folder.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            continue
    else:
        raise PlanError(f"trop de dossiers existants: {out_dir / 'clips' / base}")
    done: list[Path] = []
    for k, (n, sc) in enumerate(chosen, 1):
        d = sc.end - sc.start
        node = _node(0, 0, 0.0, d, fr, w, h, bg, cx)
        args = ["-ss", f"{sc.start:.3f}", "-t", f"{d:.3f}", "-i", str(srcs[sc.source_id]),
                "-filter_complex", node, "-map", "[v0]"]
        if use_m:  # musique : 2e entrée bouclée, coupée net à la durée du clip
            if sc.source_id not in sound:
                sound[sc.source_id] = has_audio(str(srcs[sc.source_id]))
            mix = with_a and sound[sc.source_id]  # source sans piste => musique seule
            fcx = node + ";" + _mchain(1, d, mstart, mdb, mfade, "mus" if mix else "aud")
            if mix:
                fcx += (";[0:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                        f"{_afilter(d, db)}[src];" + _duck("src", "mus", "aud"))
            i = args.index("-filter_complex")
            args[i:i + 2] = ["-stream_loop", "-1", "-i", str(mfile), "-filter_complex", fcx]
            args += ["-map", "[aud]", "-c:a", "aac", "-b:a", "192k", "-t", f"{d:.3f}"]
        elif with_a:  # "?" : source sans piste audio => clip muet, pas d'erreur
            args += ["-map", "0:a:0?", "-af", _afilter(d, db), "-c:a", "aac", "-b:a", "192k"]
        args += ["-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-movflags", "+faststart"]
        dest = folder / f"{n:03d}.mp4"
        run_ffmpeg(args, dest)
        done.append(dest)
        if on_progress is not None:
            on_progress(k, len(chosen))
    return done
