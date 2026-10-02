# MT — Project Brief

## Objectif

Construire un agent local de montage vidéo sous WSL2 et Docker. L'utilisateur dépose lui-même des vidéos dans `inbox/`. L'agent analyse ces fichiers, propose une catégorie, détecte les scènes, prépare un montage avec FFmpeg et exporte le résultat localement.

## Périmètre

Inclus :

- ingestion locale de vidéos déposées manuellement ;
- analyse technique et visuelle des vidéos ;
- proposition de catégorie ;
- détection de scènes ;
- préparation d'un plan de montage révisable ;
- rendu local avec FFmpeg ;
- export local des rendus.

Exclus :

- téléchargement de vidéos ou de médias ;
- publication, téléversement ou partage vers une plateforme externe ;
- modification ou suppression des vidéos source déposées dans `inbox/`.

## Environnement validé

Vérifié le 26 septembre 2026 dans `/home/x1_yoga2045/MT` :

- WSL : distribution Ubuntu, version par défaut WSL 2 ;
- Docker : démon accessible, Server `29.8.0` ;
- Docker Compose : `v5.5.1` ;
- FFmpeg : `/usr/bin/ffmpeg`, version `8.0.1` ;
- FFprobe : `/usr/bin/ffprobe`, version `8.0.1`.

Le dossier projet était vide lors du constat initial.

## Architecture MVP

Structure cible :

```text
MT/
  AGENTS.md
  docs/PROJECT_BRIEF.md
  inbox/          # sources déposées manuellement ; lecture seule pour l'agent
  workspace/      # proxies, images, détections, temporaires
  projects/       # plans de montage et métadonnées par vidéo
  output/         # rendus locaux finaux
  app/            # orchestrateur et modules d'analyse/montage
  docker/         # image et configuration Docker
  compose.yaml    # un seul service applicatif
```

Flux MVP : `inbox → analyse technique/visuelle → proposition de catégorie → détection de scènes → plan de montage révisable → FFmpeg → output`.

Le MVP doit utiliser un orchestrateur unique. FFprobe fournit les métadonnées techniques, une détection de scènes déterministe produit les segments, et FFmpeg réalise le rendu. Toute évolution vers plusieurs agents, une base de données ou des services additionnels exige une décision explicite avant implémentation.

## Contrats MVP validés

- Catégories initiales : `anime`, `football`, `autre`.
- Scènes : l'agent propose les scènes détectées ; il ne supprime jamais automatiquement une scène. La validation utilisateur est obligatoire avant tout montage.
- Plan de montage : JSON versionné, lisible par un humain et modifiable manuellement.
- Exports :
  - YouTube : 16:9, `1920x1080` ;
  - vertical : 9:16, `1080x1920` ;
  - conteneur : MP4 ; codec vidéo : H.264 ; codec audio : AAC.

## Décisions prises

- Le projet s'exécute localement dans WSL2 ; Docker isole l'environnement applicatif.
- Les sources proviennent uniquement du dépôt manuel dans `inbox/`.
- Le système ne télécharge rien et ne publie rien.
- `inbox/` est immuable pour l'agent : lecture seule.
- Le plan de montage doit être révisable avant rendu.
- Les exports restent locaux dans `output/`.
- Aucune application n'est encore créée ; seuls les deux fichiers de continuité existent à ce stade.

## Interdictions

- Ne pas ajouter de téléchargement, navigateur automatisé, API de publication ou intégration de plateforme externe.
- Ne pas écrire dans `inbox/`.
- Ne pas écraser une source, un plan de montage ou un export existant sans autorisation explicite.
- Ne pas dévier des contrats MVP validés sans validation explicite de l'utilisateur.
- Ne pas démarrer avec une architecture multi-agent, une base de données ou une infrastructure lourde sans besoin démontré et décision explicite.

## État actuel

Les prérequis et contrats MVP sont validés. La vidéo locale analysée n'a pas modifié `inbox/`. Son plan a reçu la validation humaine explicite de l'utilisateur. Le rendu intégral approuvé est terminé et validé localement. Le plan highlight alternatif a été rendu et validé localement : ses exports YouTube et vertical sont disponibles dans `output/`.

Fichiers présents :

- `AGENTS.md` ;
- `docs/PROJECT_BRIEF.md`.

## Traçabilité de la dernière intervention

- Décision : les deux fichiers de continuité ont été mis à jour. Le mode autonome explicitement autorisé est maintenant formalisé dans `AGENTS.md`.
- Fichiers modifiés : `AGENTS.md` et `docs/PROJECT_BRIEF.md`.
- Vérifications : l'image Docker `mt-mt` existe avec l'identifiant `sha256:eaaed0545e519b506afd185c92fb17673bade0449595fe1fe09283ec654125e4`. Le build détaché a donc finalisé l'image ; aucun conteneur de test n'a encore été exécuté.
- Problèmes rencontrés : le build a dépassé la fenêtre interactive et a dû être lancé en arrière-plan, mais aucune erreur de build n'est actuellement constatée.

## Prochaine étape exacte

Exécuter un conteneur éphémère depuis l'image `mt-mt` pour vérifier `python -m mt_agent.cli --help` et `ffmpeg -version`, puis enregistrer les résultats dans ce brief.
