# MT — Brief (2026-10-02)
Agent local de montage vidéo modulaire : noyau fiable + options. WSL2, Docker, FFmpeg. Finition manuelle dans CapCut. MT n'est pas VIDRA.

## Invariants (non négociables)
- `inbox/` en lecture seule ; aucun écrasement de source, plan ou export.
- Validation humaine avant tout rendu : seul un plan approuvé (`approved_hash`) est rendu.
- Local uniquement : pas de téléchargement, pas de publication, pas d'API payante.

## Décisions
- Refonte : on réécrit le code, on garde les idées. Rien n'est supprimé sans validation explicite.
- OpenMontage : lecture seule des noms, réécriture clean-room (AGPL). Dépôt supprimé.
- Plan JSON v2 en Pydantic : `Options`, `Source` (`offset_seconds`), `Scene` (`source_id`, `score`), `approved_hash`.
- Scènes : seuil 0,35, durée minimale 1,0 s (1,5 s pour un rendu plus posé).
- Sorties pour CapCut : clips, liste de coupes, SRT.
- Cadrage : `blur_pad` ou `crop_center` (pas de suivi de visage sur anime/football).
- Rythme : option secondaire, suspendu (phase à 140 BPM = 182 ms).
- Batch : `mt batch "inbox/*.mp4" ...` crée des plans en attente. Dashboard : Streamlit, service séparé, port 8501.

## Écarté
Génération vidéo/voix, orchestration LLM, Remotion, concat `-c copy`, cache de clips par index, uuid4, SQLite pour la déduplication.

## Bugs connus de l'ancien code
renderer : cache par index, statut d'export non sauvegardé, clip interrompu réutilisé. editor : écrasement du plan, garde erronée, division par zéro (count == 1). analyzer/planner : KeyError `duration`, code retour ffmpeg ignoré, SHA-256 recalculé. Dockerfile en CRLF, conteneur root.

## Prochaine étape
Noyau : `models.py`, fusion des scènes courtes, `plan_id`, commande `approve`, rendu réparé.
