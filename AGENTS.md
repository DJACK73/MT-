# MT — Instructions de continuité

## Règle obligatoire avant toute action

Chaque Codex doit lire intégralement `docs/PROJECT_BRIEF.md` avant toute action : analyse, commande, création, modification, suppression, installation, exécution ou rendu.

Si ce fichier est ambigu, contradictoire ou incomplet, il faut s'arrêter et demander une clarification avant toute modification du projet.

## Règle obligatoire avant de terminer

Avant de terminer son intervention, chaque Codex doit mettre à jour `docs/PROJECT_BRIEF.md` avec :

- les décisions prises et leur justification ;
- les fichiers créés, modifiés ou supprimés ;
- les vérifications réellement effectuées et leurs résultats ;
- les problèmes rencontrés, blocages ou risques ;
- la prochaine étape exacte, unique et actionnable.

Ne pas déclarer une vérification effectuée sans preuve réelle. Ne pas inventer de contrat, dépendance, comportement ou résultat.

## Portée de travail

`docs/PROJECT_BRIEF.md` est la source de vérité fonctionnelle et technique du projet MT. En cas de conflit avec une hypothèse locale, ce document prévaut jusqu'à clarification par l'utilisateur.

## Mode autonome explicitement autorisé

Lorsque l'utilisateur demande explicitement de poursuivre sans demander d'autorisation, Codex exécute les étapes normales déjà incluses dans le MVP sans confirmation intermédiaire.

- L'autorisation explicite de poursuite peut valoir validation humaine d'un plan uniquement si elle est enregistrée dans le plan JSON et dans `docs/PROJECT_BRIEF.md`.
- Codex s'arrête seulement en cas de contradiction, risque de perte de données, élargissement matériel du périmètre, échec non reproductible ou besoin réel de choix utilisateur.
- Les interdictions du brief restent applicables, notamment l'immutabilité de `inbox/`, l'absence de téléchargement de médias et l'absence de publication.
