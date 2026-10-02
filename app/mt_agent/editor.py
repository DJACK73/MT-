from .config import ROOT
from pathlib import Path
import copy
import json


def propose_highlight(plan_path, count=12):
    source_path = Path(plan_path)
    source = json.loads(source_path.read_text())
    if source["status"] == "rendered" and "proposal" in source:
        raise ValueError("Le plan est déjà une proposition de highlight.")
    candidates = [
        scene for scene in source["scenes"]
        if scene["end_seconds"] - scene["start_seconds"] >= 1
    ]
    if len(candidates) < count:
        raise ValueError("Pas assez de scènes d'au moins une seconde.")
    duration = source["scenes"][-1]["end_seconds"]
    chosen = []
    for index in range(count):
        target = duration * index / (count - 1)
        available = [scene for scene in candidates if scene["id"] not in {item["id"] for item in chosen}]
        chosen.append(min(available, key=lambda scene: abs((scene["start_seconds"] + scene["end_seconds"]) / 2 - target)))

    proposal = copy.deepcopy(source)
    proposal_id = f"{source['plan_id']}-highlights-v1"
    proposal["plan_id"] = proposal_id
    proposal["status"] = "pending_human_review"
    proposal["human_validation"] = {"approved": False, "approved_at": None}
    selected_ids = {scene["id"] for scene in chosen}
    for scene in proposal["scenes"]:
        scene["selected"] = scene["id"] in selected_ids
    for export in proposal["exports"]:
        export["output"] = f"output/{proposal_id}-{export['profile']}.mp4"
        export["status"] = "pending"
    proposal["proposal"] = {
        "kind": "highlight",
        "version": 1,
        "strategy": f"{count} scènes d'au moins une seconde, réparties uniformément ; aucune scène supprimée",
        "estimated_duration_seconds": round(sum(scene["end_seconds"] - scene["start_seconds"] for scene in chosen), 3),
    }
    output = ROOT / "projects" / f"{proposal_id}.json"
    output.write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n")
    return output
