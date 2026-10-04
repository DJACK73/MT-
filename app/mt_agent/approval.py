from __future__ import annotations
import os
import uuid
from pathlib import Path
from .models import Plan

class PlanError(RuntimeError):
    pass

def plan_id(plan: Plan) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, plan.content_hash()))

def is_approved(plan: Plan) -> bool:
    return plan.status == "approved" and plan.approved_hash == plan.content_hash()

def approve(plan: Plan) -> Plan:
    if plan.status == "rendered":
        raise PlanError("plan déjà rendu")
    return plan.model_copy(update={"status": "approved", "approved_hash": plan.content_hash()})

def assert_renderable(plan: Plan) -> None:
    if not is_approved(plan):
        raise PlanError("plan non approuvé ou modifié depuis l'approbation")

def save_plan(plan: Plan, directory: Path) -> Path:
    """Nom = plan_id + statut : ne remplace jamais un plan existant."""
    directory.mkdir(parents=True, exist_ok=True)
    out = directory / f"{plan_id(plan)}.{plan.status}.json"
    part = out.with_name(out.name + ".part")
    part.write_text(plan.model_dump_json(indent=2))
    try:
        os.link(part, out)  # échoue si out existe
    except FileExistsError as e:
        raise PlanError(f"refus d'écraser: {out}") from e
    finally:
        part.unlink(missing_ok=True)
    return out
