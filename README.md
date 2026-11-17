# MT

Agent local de montage vidéo. Aucun téléchargement ni publication.

## Usage local

```bash
PYTHONPATH=app python3 -m mt_agent.cmd --help
```

`scan` crée un plan en attente de revue. `propose-highlight` crée un second plan non approuvé et conserve toutes les scènes. `render` refuse tout plan sans validation humaine enregistrée.

Les sources dans `inbox/` ne sont jamais modifiées. Les exports sont dans `output/`.
