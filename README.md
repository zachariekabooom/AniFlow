# AniFlow

![Logo AniFlow](docs/branding/aniflow-logo-final.png)

AniFlow est une application de bureau Windows 11 destinée à rechercher des animés, construire et personnaliser leur chronologie complète, organiser une bibliothèque personnelle, lire des fichiers locaux, gérer les téléchargements compatibles et présenter des statistiques détaillées.

**État actuel :** phase 0 — preuves de faisabilité obtenues sous Windows 11 (AniList réel, libmpv, Qt, Ollama avec Gemma 4 E2B/E4B ; 123 tests passants sous Windows et sous Linux) ; deux confirmations non techniques restent avant de cocher la phase. Voir `PROJECT_STATUS.md`.

## Source de vérité du projet

- `SPEC.md` — cahier des charges fonctionnel et technique complet.
- `PROJECT_STATUS.md` — point de reprise court et actuel ; à lire en premier à chaque session Claude.
- `ROADMAP.md` — phases obligatoires vers l'application complète.
- `DECISIONS.md` — décisions d'architecture et choix encore ouverts.
- `DEV_LOG.md` — journal concis des changements et des résultats de test observés.
- `CLAUDE_MASTER_PROMPT.md` — prompt de lancement pour Claude.
- `CLAUDE_WORKFLOW.md` — règles de développement, de test et de gestion du contexte.
- `CLAUDE_SESSION_TEMPLATE.md` — modèle bref pour une nouvelle session lorsque le contexte précédent est épuisé.
- `GITHUB_SETUP.md` — réglages et mise en place du dépôt GitHub.
- `docs/branding/aniflow-logo-final.png` — logo approuvé.

## Principes non négociables

- Thème sombre moderne et minimaliste, bleu marine très foncé avec accents bleu électrique.
- Le mode principal de visionnage inclut par défaut tous les contenus identifiés, y compris les récapitulatifs. Les incertitudes restent visibles et chaque élément peut être réordonné par glisser-déposer.
- Toute fonctionnalité qui utilise une IA utilise exclusivement un modèle local. Pas d'API d'IA distante ni de fallback cloud.
- Les téléchargements se limitent aux sources et médias accessibles dans un cadre autorisé ; aucun contournement des DRM ou des contrôles d'accès.
- Le logiciel complet est réalisé par phases vérifiables. Il ne doit pas être réduit à un prototype jetable.
- Aucun test ou résultat ne peut être annoncé comme réussi sans exécution réelle.

## Développement

Démarrage rapide (Python 3.12, 64 bits) :

```powershell
py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -e ".[ui,player]"
python -m unittest discover -s tests -t .
```

Validation de la phase 0 sur Windows : `docs/phase0/validation-windows.md`.

Consulter `GITHUB_SETUP.md` pour créer le dépôt, puis `CLAUDE_MASTER_PROMPT.md` pour démarrer. Ne versionner ni vidéos, ni modèles IA, ni bases personnelles, ni secrets, ni environnements virtuels. Voir `.gitignore`.

## Utilisation dans un projet Claude

Copier le contenu de `CLAUDE_PROJECT_INSTRUCTIONS.md` dans le champ « Instructions du projet » de Claude. Ajouter ensuite les documents de référence listés dans `CLAUDE_WORKFLOW.md` à la base de connaissances du projet. Le prompt maître reste un message de lancement de développement, pas une instruction à réexécuter automatiquement dans chaque discussion.
