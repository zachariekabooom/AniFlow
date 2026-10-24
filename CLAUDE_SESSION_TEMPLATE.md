# Prompt bref de reprise Claude

Lis d’abord `PROJECT_STATUS.md`. Lis ensuite uniquement la phase active de `ROADMAP.md`, les sections pertinentes de `SPEC.md`, les décisions utiles de `DECISIONS.md` et les dernières entrées pertinentes de `DEV_LOG.md`.

Reprends la prochaine tâche unique indiquée dans `PROJECT_STATUS.md`. Ne recommence pas la planification. Inspecte `git status`, `git log -5 --oneline` et les fichiers qui concernent cette tâche. Implémente un bloc cohérent, exécute les tests utiles, inspecte le diff, puis mets à jour `PROJECT_STATUS.md`, `ROADMAP.md` et `DEV_LOG.md`. Aucun appel IA cloud ; si une fonction utilise de l’IA, passe uniquement par le modèle local configuré. N’affirme jamais un test ou un commit non exécuté. Si la tâche ne tient pas dans cette session, fais un checkpoint propre et indique une prochaine tâche précise.

**Tâche courante à conserver :** celle du `PROJECT_STATUS.md`. N’en invente pas une nouvelle si celle-ci est claire.
