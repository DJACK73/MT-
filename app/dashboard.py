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
from mt_agent.preview import preview_clip

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
        _switch(save_plan(select_scenes(load(path), st.session_state.get("spec", "")), path.parent))
    except ERRORS as e:
        _flash("error", str(e))


def on_approve() -> None:
    path = Path(st.session_state["plan_path"])
    try:
        _switch(save_plan(approve(load(path)), path.parent))
    except ERRORS as e:
        _flash("error", str(e))


def main() -> None:
    st.set_page_config(page_title="MT", layout="wide")
    st.title("MT")
    flash = st.session_state.pop("flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])
    plans = list_plans(PLANS)
    if not plans:
        st.info("Aucun plan dans workspace/plans. Lancer `scan` d'abord.")
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
    cols = st.columns(COLS)
    for i, (sc, t) in enumerate(zip(plan.scenes, thumbs), 1):
        with cols[(i - 1) % COLS]:
            st.image(str(t), caption=f"{i} · {sc.end - sc.start:.1f}s {'✔' if sc.selected else '·'}")
    n = int(st.number_input("Aperçu : scène n°", 1, len(plan.scenes), 1, key="prev_n"))
    cur = plan.scenes[n - 1]
    st.caption(f"Scène {n} : {cur.start:.2f} à {cur.end:.2f} s ({cur.end - cur.start:.1f} s)")
    srcs = {x.id: Path(x.path) if Path(x.path).is_absolute() else ROOT / x.path for x in plan.sources}
    try:
        with st.spinner("Extraction de l'aperçu…"):
            clip = preview_clip(srcs[cur.source_id], cur.start, cur.end, ROOT)
        st.video(str(clip))
    except Exception as e:  # bord UI : afficher l'erreur sans planter la page
        st.error(f"Aperçu impossible : {e}")
    st.text_input("Sélection (ex. 1-5,8)", key="spec")
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


main()
