from __future__ import annotations
from pathlib import Path
import streamlit as st
from pydantic import ValidationError
from mt_agent.approval import PlanError, approve, is_approved, save_plan
from mt_agent.export import export_plan
from mt_agent.models import Plan
from mt_agent.paths import ROOT
from mt_agent.selection import select_scenes
from mt_agent.thumbs import make_thumbnails
from mt_agent.selection import spec_from_flags
from mt_agent.preview import preview_clip
from mt_agent.fit import window_flag
from mt_agent.clean import plan_clean, run_clean, size_of

PLANS = ROOT / "workspace" / "plans"
ERRORS = (PlanError, ValidationError, ValueError, OSError, RuntimeError)
COLS = 6


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


def on_select() -> None:
    path = Path(st.session_state["plan_path"])
    try:
        plan = load(path)
        spec = st.session_state.get("spec", "").strip()
        if not spec:
            spec = spec_from_flags([bool(st.session_state.get(f"sel:{path.name}:{i}"))
                                    for i in range(1, len(plan.scenes) + 1)])
        if not spec:
            _flash("error", "Aucune scène cochée ni numéro saisi")
            return
        _switch(save_plan(select_scenes(plan, spec), path.parent))
        st.session_state["spec"] = ""
    except ERRORS as e:
        _flash("error", str(e))


def on_approve() -> None:
    path = Path(st.session_state["plan_path"])
    try:
        _switch(save_plan(approve(load(path)), path.parent))
    except ERRORS as e:
        _flash("error", str(e))


@st.dialog("Aperçu", width="large")
def show_clip(i: int) -> None:
    plan = load(Path(st.session_state["plan_path"]))
    sc = plan.scenes[i - 1]
    srcs = {x.id: Path(x.path) if Path(x.path).is_absolute() else ROOT / x.path for x in plan.sources}
    st.caption(f"Scène {i} : {sc.start:.2f} à {sc.end:.2f} s · durée {sc.end - sc.start:.2f} s")
    try:
        st.video(str(preview_clip(srcs[sc.source_id], sc.start, sc.end, ROOT)))
    except Exception as e:  # bord UI : afficher l'erreur sans planter la page
        st.error(f"Aperçu impossible : {e}")


def on_all(value: bool) -> None:
    path = Path(st.session_state["plan_path"])
    for i in range(1, len(load(path).scenes) + 1):
        st.session_state[f"sel:{path.name}:{i}"] = value


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
    st.divider()
    st.subheader("Nettoyage")
    st.caption("À faire une fois les exports terminés. Confirmation demandée. workspace/archive-* n'est jamais touché.")
    for lvl, col in zip((1, 2, 3), st.columns(3)):
        if col.button(CLEAN_LABELS[lvl], key=f"clean_{lvl}"):
            confirm_clean(lvl)


def main() -> None:
    st.set_page_config(page_title="MT", layout="wide")
    st.title("MT")
    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])
    plans = list_plans(PLANS)
    if not plans:
        st.info("Aucun plan dans workspace/plans. Lancer `scan` d'abord.")
        render_clean()
        return
    st.selectbox("Plan", plans, key="plan_path", format_func=lambda s: Path(s).name)
    path = Path(st.session_state["plan_path"])
    plan = load(path)
    kept = sum(s.end - s.start for s in plan.scenes if s.selected)
    c1, c2, c3 = st.columns(3)
    c1.metric("Statut", plan.status)
    c2.metric("Scènes", f"{sum(s.selected for s in plan.scenes)}/{len(plan.scenes)}")
    c3.metric("Durée retenue", f"{kept:.1f} s")
    thumbs = make_thumbnails(plan, ROOT)
    if len(thumbs) != len(plan.scenes):
        st.warning(f"{len(thumbs)} vignettes pour {len(plan.scenes)} scènes")
    pk = Path(st.session_state["plan_path"]).name
    m1, m2, _ = st.columns([1, 1, 6])
    lo = m1.number_input("Min (s)", 0.0, 60.0, 3.0, 0.5, key="win_lo")
    hi = m2.number_input("Max (s)", 0.5, 120.0, 5.0, 0.5, key="win_hi")
    bad = sum(1 for x in plan.scenes if window_flag(x.end - x.start, lo, hi))
    st.caption(f"Hors fenêtre {lo:g}–{hi:g} s : {bad} scène(s). ▼ trop courte, ▲ trop longue.")
    cols = st.columns(COLS)
    for i, (sc, t) in enumerate(zip(plan.scenes, thumbs), 1):
        with cols[(i - 1) % COLS]:
            dur = sc.end - sc.start
            st.image(str(t), caption=f"{i} · {dur:.2f}s {window_flag(dur, lo, hi)}".rstrip())
            k = f"sel:{pk}:{i}"
            if k not in st.session_state:
                st.session_state[k] = sc.selected
            st.checkbox("garder", key=k)
            if st.button("▶ voir", key=f"v:{pk}:{i}"):
                show_clip(i)
    flags = [bool(st.session_state.get(f"sel:{pk}:{i}")) for i in range(1, len(plan.scenes) + 1)]
    st.caption(f"Cochées : {sum(flags)}/{len(flags)}")
    b1, b2, _ = st.columns([1, 1, 6])
    b1.button("Tout cocher", on_click=on_all, args=(True,))
    b2.button("Tout décocher", on_click=on_all, args=(False,))
    st.text_input("Sélection (ex. 1-5,8)", key="spec")
    st.caption("Si ce champ est rempli, il remplace les cases cochées.")
    st.button("Appliquer la sélection", on_click=on_select)
    st.button("Approuver", on_click=on_approve, disabled=plan.status != "pending_human_review")
    if st.button("Exporter", disabled=not is_approved(plan)):
        with st.spinner("Rendu en cours…"):
            try:
                mp4, done = export_plan(plan, ROOT, ROOT / "output")
            except ERRORS as e:
                st.error(str(e))
            else:
                st.success(f"{mp4.name} · {done.name}")

    render_clean()

main()
