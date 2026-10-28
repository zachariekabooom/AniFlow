# Workflow de développement avec Claude et GitHub

Ce fichier complète `CLAUDE_MASTER_PROMPT.md`. Pour les paramètres pas à pas et la procédure de connexion Claude, voir `GITHUB_SETUP.md`.

## 1. Mise en place de GitHub

1. Utiliser le dépôt GitHub `AniFlow` : **public**, choix explicite du propriétaire (voir `DECISIONS.md`). Ne jamais y committer de base de données, de rapport généré, de DLL, de modèle, de vidéo, d'archive ni de secret.
2. Copier les fichiers du kit à la racine du dépôt.
3. Utiliser le `.gitignore` fourni et vérifier qu’il exclut les environnements virtuels, `.env`, clés/secrets, modèles IA, vidéos, bases personnelles, caches, logs et fichiers temporaires. Il doit exclure au minimum les environnements virtuels, `.env`, clés/secrets, modèles IA, vidéos, bases personnelles, caches, logs et fichiers temporaires.
4. Réaliser un premier commit dédié à la planification : `docs: add AniFlow specification and project plan`.
5. Garder `main` pour les états stables. Pour les changements risqués, travailler sur une branche courte telle que `feature/watch-order-drag-drop`, puis vérifier les tests avant fusion.
6. Faire un commit quand un ensemble cohérent passe les tests, plutôt qu'un commit par petite ligne. Les tags/releases représentent les étapes stables.
7. Conserver une sauvegarde supplémentaire des documents importants, mais ne pas dupliquer ou versionner les fichiers vidéo et modèles. Git est un historique de code, pas une sauvegarde des médias personnels.

## 2. Comment Claude doit travailler

- Toujours lire `PROJECT_STATUS.md` en premier.
- Lire uniquement les parties de la spécification nécessaires à la tâche actuelle.
- Avant de coder, déclarer l'objectif, les fichiers qui devraient changer et les tests d'acceptation.
- Réaliser une tâche fonctionnelle à la fois, en plusieurs sous-étapes si nécessaire.
- Examiner les modules existants avant d'en créer de nouveaux ; ne pas réécrire une fonctionnalité stable sans raison.
- Avant d'adapter un projet open source, vérifier la licence, la maintenance, les dépendances, les conditions d'intégration et les risques de sécurité. Citer la source dans `DECISIONS.md` ou la documentation de dépendance.
- Ne pas aspirer le dépôt entier dans le contexte à chaque tour. Utiliser recherche ciblée, lectures par sections, `git status`, `git diff` et tests concernés.
- Ne pas inclure les modèles, vidéos, caches et bases locales dans le dépôt ni les fournir comme contexte systématique.

## 3. Fin de session obligatoire

Avant de terminer :

1. Lancer les tests pertinents ; indiquer les commandes exactes et leur sortie utile.
2. Dire clairement ce qui n'a pas été testé ou dépend d'un accès manquant.
3. Examiner le diff et vérifier qu'aucun secret ou fichier personnel n'a été ajouté.
4. Mettre à jour `PROJECT_STATUS.md`, `ROADMAP.md` et `DEV_LOG.md`; mettre à jour `DECISIONS.md` si un choix a changé.
5. Donner un prochain objectif unique, petit et précis.
6. Créer un commit si le changement constitue un jalon cohérent et vérifié ; ne jamais prétendre qu'un commit ou un test a réussi sans l'avoir exécuté.

## 4. GitHub ne remplace pas le fichier d'état

Les commits indiquent ce qui a changé dans le code, mais ne décrivent pas toujours ce que Claude doit faire ensuite. `PROJECT_STATUS.md` donne le dernier commit stable, l'état réel, les points non testés et la prochaine tâche. Si une intégration Claude ne transmet pas l'historique Git ou les discussions précédentes, ce fichier permet de reprendre sans recharger toute la conversation.

## 5. Fichier `.gitignore` recommandé

À adapter si l'architecture change :

```gitignore
.venv/
venv/
__pycache__/
*.py[cod]
.env
.env.*
!.env.example
*.log
logs/
.cache/
cache/
models/
*.gguf
*.safetensors
media/
Videos/
Downloads/
*.db
*.sqlite
*.sqlite3
*.part
*.tmp
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.spec
.DS_Store
Thumbs.db
```

La base SQLite d'exemple ou les fixtures de test peuvent être suivies si elles sont petites, synthétiques et clairement identifiées ; ne jamais versionner la base personnelle réelle.
