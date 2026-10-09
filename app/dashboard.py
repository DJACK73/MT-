from __future__ import annotations
from pathlib import Path
import streamlit as st
from pydantic import ValidationError
from mt_agent.approval import PlanError, approve, is_approved, plan_id, save_plan
from mt_agent.cmd import scan_video
from mt_agent.ffx import MediaError
from mt_agent.export import Look, export_clips, export_plan
from mt_agent.models import Options, Plan
from mt_agent.paths import ROOT
from mt_agent.selection import select_scenes
from mt_agent.thumbs import make_thumbnails
from mt_agent.selection import spec_from_flags
from mt_agent.preview import preview_clip
from mt_agent.fit import window_flag
from mt_agent.clean import plan_clean, run_clean, size_of

PLANS = ROOT / "workspace" / "plans"
ERRORS = (PlanError, ValidationError, ValueError, OSError, RuntimeError, MediaError)
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}
COLS = 5
STATUS_FR = {"pending_human_review": "À valider", "approved": "Approuvé", "rendered": "Rendu"}
CSS = (
    "<style>.block-container{padding-top:1.5rem}"
    "[data-testid='stImage'] img{border-radius:8px}"
    "button[kind='primary'],[data-testid='stBaseButton-primary']{background-color:#16a34a;border-color:#16a34a;color:#fff}"
    "button[kind='primary']:hover,[data-testid='stBaseButton-primary']:hover{background-color:#15803d;border-color:#15803d;color:#fff}"
    "[class*='st-key-card_']{border-radius:12px;transition:all .15s}"
    "[class*='st-key-card_']:has(input:checked){box-shadow:0 0 0 2px #16a34a;background:rgba(22,163,74,.10)}"
    "[class*='st-key-card_']:has(input:not(:checked)){opacity:.55}"
    "[class*='st-key-card_']:hover{opacity:1}"
    "</style>"
)


def load(p: Path) -> Plan:
    return Plan.model_validate_json(p.read_text())


def list_plans(d: Path) -> list[str]:
    if not d.is_dir():
        return []
    files = sorted((x for x in d.iterdir() if x.is_file()), key=lambda x: x.stat().st_mtime, reverse=True)
    out: list[str] = []
    for p in files:
        try:
            load(p)
        except ERRORS:
            continue
        out.append(str(p))
    return out


def _flash(kind: str, msg: str) -> None:
    st.session_state["flash"] = (kind, msg)


def _switch(new: Path) -> None:
    st.session_state["plan_path"] = str(new)
    _flash("success", f"plan écrit : {new.name}")


def _flags(plan: Plan, pk: str) -> list[bool]:
    return [bool(st.session_state.get(f"sel:{pk}:{i}", sc.selected)) for i, sc in enumerate(plan.scenes, 1)]


def plan_label(p: str) -> str:
    pl = load(Path(p))
    stem = Path(pl.sources[0].path).stem if pl.sources else "?"
    return f"{STATUS_FR[pl.status]} · {stem} · {sum(s.selected for s in pl.scenes)}/{len(pl.scenes)} scènes · {Path(p).name[:8]}"


def on_select() -> None:
    path = Path(st.session_state["plan_path"])
    try:
        plan = load(path)
        spec = st.session_state.get("spec", "").strip()
        if not spec:
            spec = spec_from_flags(_flags(plan, path.name))
        if not spec:
            _flash("error", "Aucune scène cochée ni numéro saisi")
            return
        new = select_scenes(plan, spec)
        if new.content_hash() == plan.content_hash():
            st.session_state["spec"] = ""
            _flash("info", "Sélection déjà enregistrée : rien à changer")
            return
        _switch(save_plan(new, path.parent))
        st.session_state["spec"] = ""
    except ERRORS as e:
        _flash("error", str(e))


def on_approve() -> None:
    path = Path(st.session_state["plan_path"])
    try:
        _switch(save_plan(approve(load(path)), path.parent))
    except ERRORS as e:
        _flash("error", str(e))


def _pv_move(step: int, n: int) -> None:
    st.session_state["pv"] = min(max(int(st.session_state.get("pv", 1)) + step, 1), n)


@st.dialog("Aperçu", width="small")
def show_clip() -> None:
    path = Path(st.session_state["plan_path"])
    plan = load(path)
    n = len(plan.scenes)
    i = min(max(int(st.session_state.get("pv", 1)), 1), n)
    sc = plan.scenes[i - 1]
    srcs = {x.id: Path(x.path) if Path(x.path).is_absolute() else ROOT / x.path for x in plan.sources}
    kept = bool(st.session_state.get(f"sel:{path.name}:{i}", sc.selected))
    st.markdown(f"**Scène {i}/{n}** · {sc.end - sc.start:.2f} s · " + (":green[✓ gardée]" if kept else ":red[✗ non gardée]"))
    st.caption(f"{sc.start:.2f} → {sc.end:.2f} s dans la source")
    try:
        with st.spinner("Préparation de l'aperçu…"):
            clip = preview_clip(srcs[sc.source_id], sc.start, sc.end, ROOT)
        st.video(str(clip))
    except Exception as e:  # bord UI : afficher l'erreur sans planter la page
        st.error(f"Aperçu impossible : {e}")
    c1, c2 = st.columns(2)
    c1.button("◀ Précédente", key="pv_prev", on_click=_pv_move, args=(-1, n), disabled=i <= 1, use_container_width=True)
    c2.button("Suivante ▶", key="pv_next", on_click=_pv_move, args=(1, n), disabled=i >= n, use_container_width=True)
    if st.button("OK, retour aux scènes", type="primary", key="pv_ok", use_container_width=True):
        st.rerun()


def list_videos(d: Path) -> list[str]:
    if not d.is_dir():
        return []
    return sorted(x.name for x in d.iterdir() if x.is_file() and x.suffix.lower() in VIDEO_EXT)


def render_scan() -> None:
    videos = list_videos(ROOT / "inbox")
    if not videos:
        st.info("Aucune vidéo dans inbox/. Dépose-en via l'Explorateur, puis recharge la page.")
        return
    st.selectbox("Vidéo (inbox/)", videos, key="scan_video")
    s1, s2, _ = st.columns([1, 1, 6])
    lo = s1.number_input("Min (s)", 0.5, 60.0, 3.0, 0.5, key="scan_lo")
    hi = s2.number_input("Max (s)", 0.5, 120.0, 5.0, 0.5, key="scan_hi")
    st.caption("Les durées sont fixées à la découpe : changer Min/Max puis Découper crée un nouveau plan.")

    def _window(lo_: float, hi_: float) -> None:
        st.session_state["scan_lo"], st.session_state["scan_hi"] = lo_, hi_

    w1, w2, _ = st.columns([1, 1, 6])
    w1.button("Fenêtre 3–4 s", on_click=_window, args=(3.0, 4.0), use_container_width=True)
    w2.button("Fenêtre 3–5 s", on_click=_window, args=(3.0, 5.0), use_container_width=True)
    b1, b2, _ = st.columns([1, 1.4, 5])
    one = b1.button("Découper", type="primary", use_container_width=True)
    many = len(videos) > 1 and b2.button(f"Découper les {len(videos)} vidéos", use_container_width=True)
    if not (one or many):
        return
    if hi < lo:
        st.error("Max doit être supérieur ou égal à Min")
        return
    targets = videos if many else [st.session_state["scan_video"]]
    opt = Options(min_scene_seconds=lo, max_scene_seconds=hi)
    PLANS.mkdir(parents=True, exist_ok=True)
    bar = st.progress(0.0, text="Découpe…")
    made: list[int] = []
    existed = 0
    errors: list[str] = []
    last: Path | None = None
    for k, name in enumerate(targets, 1):
        bar.progress((k - 1) / len(targets), text=f"Découpe {k}/{len(targets)} : {name}")
        try:
            plan = scan_video(ROOT / "inbox" / name, ROOT, opt, True)
            target = PLANS / f"{plan_id(plan)}.{plan.status}.json"
            if target.exists():
                existed += 1
                last = target
            else:
                last = save_plan(plan, PLANS)
                made.append(len(plan.scenes))
        except ERRORS as e:
            errors.append(f"{name}: {e}")
    bar.empty()
    if last is not None:
        st.session_state["plan_path"] = str(last)
    parts: list[str] = []
    if made:
        parts.append(f"{len(made)} plan(s) créé(s), {sum(made)} scènes (fenêtre {lo:g}–{hi:g} s)")
    if existed:
        parts.append(f"{existed} déjà découpé(s) avec ces durées : rouvert(s)")
    if errors:
        parts.append("erreurs : " + "; ".join(errors))
    _flash("error" if errors else ("success" if made else "info"), " · ".join(parts))
    st.rerun()


def on_all(value: bool) -> None:
    path = Path(st.session_state["plan_path"])
    for i in range(1, len(load(path).scenes) + 1):
        st.session_state[f"sel:{path.name}:{i}"] = value


def on_invert() -> None:
    path = Path(st.session_state["plan_path"])
    for i, sc in enumerate(load(path).scenes, 1):
        k = f"sel:{path.name}:{i}"
        st.session_state[k] = not bool(st.session_state.get(k, sc.selected))


CLEAN_LABELS = {
    1: "Nettoyer les découpes",
    2: "Nettoyer découpes + output",
    3: "Nettoyer découpes + output + inbox",
}


@st.dialog("Confirmer le nettoyage")
def confirm_clean(level: int) -> None:
    todo = plan_clean(ROOT, level)
    total = sum(size_of(p) for p in todo)
    st.write(f"{CLEAN_LABELS[level]} : {len(todo)} élément(s), {total / 1e6:.1f} Mo. Irréversible.")
    if level == 3:
        st.warning("Les vidéos originales de inbox/ seront supprimées.")
    if st.button("Confirmer", type="primary", key=f"clean_ok_{level}"):
        try:
            done, errs = run_clean(ROOT, level)
        except ERRORS as e:
            _flash("error", str(e))
        else:
            msg = f"{done} élément(s) supprimé(s)"
            if errs:
                msg += " · erreurs : " + "; ".join(errs)
            _flash("error" if errs else "success", msg)
        st.session_state.pop("plan_path", None)
        st.rerun()


def render_clean() -> None:
    with st.expander("Nettoyage (à faire à la fin, après les exports)"):
        st.caption("Confirmation demandée. workspace/archive-* n'est jamais touché.")
        st.caption("Pour vider inbox/ : supprime les vidéos dans l'Explorateur Windows (inbox/ est en lecture seule ici).")
        for lvl, col in zip((1, 2), st.columns(2)):
            if col.button(CLEAN_LABELS[lvl], key=f"clean_{lvl}", use_container_width=True):
                confirm_clean(lvl)


def _export_video(plan: Plan, look: Look) -> None:
    with st.spinner("Rendu de la vidéo en cours (plusieurs minutes possibles)…"):
        try:
            mp4, _ = export_plan(plan, ROOT, ROOT / "output", look=look)
        except ERRORS as e:
            st.error(str(e))
            return
    st.success(f"Vidéo prête : output/{mp4.name}")


def _export_clips(plan: Plan, look: Look) -> None:
    bar = st.progress(0.0, text="Rendu des clips…")

    def tick(k: int, n: int) -> None:
        bar.progress(k / n, text=f"Clip {k}/{n}")

    try:
        files = export_clips(plan, ROOT, ROOT / "output", on_progress=tick, look=look)
    except ERRORS as e:
        bar.empty()
        st.error(str(e))
        return
    bar.empty()
    st.success(f"{len(files)} clips prêts : {files[0].parent.relative_to(ROOT)}")


def main() -> None:
    st.set_page_config(page_title="MT", page_icon="🎬", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🎬 MT · Montage")
    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])
    plans = list_plans(PLANS)
    with st.expander("① Découper une vidéo", expanded=True):
        render_scan()
    if not plans:
        st.info("Aucun plan pour l'instant : découpe une vidéo ci-dessus.")
        render_clean()
        return
    st.selectbox("② Plan à monter", plans, key="plan_path", format_func=plan_label)
    path = Path(st.session_state["plan_path"])
    plan = load(path)
    pk = path.name
    saved = [s.selected for s in plan.scenes]
    flags = _flags(plan, pk)
    spec = str(st.session_state.get("spec", "")).strip()
    dirty = bool(spec) or flags != saved
    pending = plan.status == "pending_human_review"
    approved = is_approved(plan)
    kept = sum(s.end - s.start for s in plan.scenes if s.selected)
    c1, c2, c3 = st.columns(3)
    c1.metric("Statut", STATUS_FR[plan.status])
    c2.metric("Scènes", f"{sum(saved)}/{len(saved)}")
    c3.metric("Durée retenue", f"{kept:.1f} s")
    saved_any = any(saved)
    if plan.status == "rendered" and not dirty:
        step = 4
    elif approved and not dirty:
        step = 3
    elif saved_any and not dirty:
        step = 2
    else:
        step = 1
    labels = ["Découper", "Choisir", "Approuver", "Exporter"]
    st.markdown("  →  ".join(
        f":green[✓ {n}]" if j < step else f"**:orange[● {n}]**" if j == step else f":gray[{n}]"
        for j, n in enumerate(labels)))
    lo = plan.options.min_scene_seconds
    mx = plan.options.max_scene_seconds
    hi = float("inf") if mx is None else mx
    bad = sum(1 for x in plan.scenes if window_flag(x.end - x.start, lo, hi))
    if mx is not None and bad * 2 > len(plan.scenes):
        st.warning(f"{bad}/{len(plan.scenes)} scènes hors fenêtre : la fenêtre {lo:g}–{mx:g} s est trop étroite. "
                   "Refais la découpe avec un Max plus grand (ex. 5 s) dans « ① Découper une vidéo ».")
    if dirty:
        st.warning("Sélection modifiée, pas encore enregistrée : clique « Appliquer la sélection ».")
    elif plan.status == "rendered":
        st.success("Plan déjà rendu.")
    elif approved:
        st.success("Approuvé : choisis un export ci-dessous.")
    elif plan.status == "approved":
        st.warning("Plan modifié depuis l'approbation : approbation invalide.")
    elif not saved_any:
        st.info("Coche les scènes à garder (ou saisis des numéros), puis « Appliquer la sélection ».")
    else:
        st.info("Sélection enregistrée : clique « Approuver » pour débloquer l'export.")
    t1, t2, t3, t4 = st.columns([1, 1, 1, 3])
    t1.button("Tout cocher", on_click=on_all, args=(True,), use_container_width=True)
    t2.button("Tout décocher", on_click=on_all, args=(False,), use_container_width=True)
    t3.button("Inverser", on_click=on_invert, use_container_width=True)
    t4.caption(f"Cochées : {sum(flags)}/{len(flags)}")
    r1, r2, r3 = st.columns([2, 1.2, 2])
    fit = r1.radio("Cadrage 9:16", ["Bandes (image entière)", "Plein cadre (recadré)"], key="look_fit", horizontal=True)
    full = fit.startswith("Plein")
    bgc = r2.radio("Fond des bandes", ["Flou", "Noir"], key="look_bg", horizontal=True, disabled=full)
    pos = r3.slider("Position du recadrage", 0, 100, 50, key="look_pos", disabled=not full,
                    help="0 = bord gauche, 100 = bord droit. Valable pour toutes les scènes.")
    look = Look(fit="fill" if full else "bars", background="black" if bgc == "Noir" else "blur", anchor=pos / 100)
    a1, a2, a3, a4 = st.columns(4)
    a1.button("Appliquer la sélection", on_click=on_select,
              type="primary" if dirty else "secondary", use_container_width=True)
    a2.button("Approuver", on_click=on_approve,
              type="primary" if pending and not dirty and any(saved) else "secondary",
              disabled=not pending or dirty or not any(saved), use_container_width=True)
    go_video = a3.button("Exporter la vidéo assemblée", type="primary" if approved and not dirty else "secondary",
                         disabled=not approved or dirty, use_container_width=True)
    go_clips = a4.button("Exporter en clips séparés", disabled=not approved or dirty, use_container_width=True)
    if approved and not dirty:
        st.caption(f"Rendu estimé : environ {max(1, round(kept / 0.33 / 60))} min au plus (mesuré avec le cadrage flou).")
    if go_video:
        _export_video(plan, look)
    if go_clips:
        _export_clips(plan, look)
    with st.expander("Sélection par numéros (avancé)"):
        st.text_input("Sélection (ex. 1-5,8)", key="spec")
        st.caption("Si ce champ est rempli, il remplace les cases cochées.")
    thumbs = make_thumbnails(plan, ROOT)
    if len(thumbs) != len(plan.scenes):
        st.warning(f"{len(thumbs)} vignettes pour {len(plan.scenes)} scènes")
    if mx is None:
        st.caption(f"Plan découpé avec min {lo:g} s, sans max.")
    else:
        st.caption(f"Plan découpé en fenêtre {lo:g}–{mx:g} s : {bad} scène(s) hors fenêtre. ▼ trop courte, ▲ trop longue.")
    cols = st.columns(COLS)
    for i, (sc, th) in enumerate(zip(plan.scenes, thumbs), 1):
        with cols[(i - 1) % COLS], st.container(border=True, key=f"card_{i}"):
            dur = sc.end - sc.start
            flag = window_flag(dur, lo, hi)
            st.image(str(th))
            st.caption(f"**{i}** · {dur:.2f} s" + (f" :orange[{flag}]" if flag else ""))
            k = f"sel:{pk}:{i}"
            if k not in st.session_state:
                st.session_state[k] = sc.selected
            g, v = st.columns([1, 1])
            g.checkbox("garder", key=k)
            if v.button("▶ voir", key=f"v:{pk}:{i}", use_container_width=True):
                st.session_state["pv"] = i
                show_clip()
    render_clean()

main()
