# Phase 1 — plan de développement (approuvé le 26 octobre 2026)

> Ce fichier conserve le plan E0–E8 approuvé par l'utilisateur, pour reprendre sans la conversation. L'avancement fait foi dans `ROADMAP.md` et `PROJECT_STATUS.md`.

## Décisions de l'utilisateur (26/10/2026)

1. Périmètre conservé : fenêtre principale, navigation, composants, tests et page Paramètres minimale.
2. Restauration des sauvegardes (interface) : reportée à la phase 7.
3. PySide6 : 6.12.0, version installée sur le PC de l'utilisateur.
4. Icônes : Lucide, avec conservation des avis de licence nécessaires (licence à re-vérifier avant intégration, étape E4).
5. Licence du code source : choix reporté. Usage personnel uniquement ; aucun binaire distribué avant décision explicite de licence.
6. Dépôt GitHub public, volontairement. Aucun audit de l'historique n'est demandé.
7. Git : fusion de `phase0-integration` dans `main`, tag de validation de la phase 0, puis branche `phase1`. Les commandes sont exécutées par l'utilisateur.

## Règles de travail

- Une étape = une archive incrémentale + les sorties de tests réellement exécutées. Un critère qui dépend d'une validation sur le PC de l'utilisateur n'est pas coché tant que le résultat n'est pas communiqué.
- L'assistant ne peut pas exécuter PySide6 : il teste la logique pure ; les widgets restent minces et sont validés sous Windows (tests hors écran + checklist visuelle).
- Pas de bouton factice : une section non livrée affiche un état vide honnête (« Disponible en phase N »).

## Étapes

**E0 — clôture documentaire de la phase 0** · statut : documents livrés ; fusion, tag et branche à exécuter par l'utilisateur.
- Critères : phase 0 à 8/8 dans `ROADMAP.md` ; plus aucune affirmation de dépôt privé ou de visibilité non confirmée ; tag `phase0-validee` posé par l'utilisateur.

**E1 — logique pure et garde-fous (sans Qt)** · statut : livré, testé sous Linux ; exécution sous Windows en attente.
- Livre : `ui/navigation.py` (6 sections de SPEC §11, identifiants persistés, raccourcis Ctrl+1…6), clés `ui.last_section` et `ui.window_geometry`, `startup.py` (contrôles de démarrage), `ui/errors.py` (messages utilisateur), garde-fous de dépôt public (`tests/test_repo_hygiene.py`, `tests/test_no_hardcoded_colors.py`).
- Critères : ordre exact des sections (aussi comparé à la ligne de SPEC §11) ; identifiants et raccourcis uniques ; valeur hors liste refusée avec message français ; base plus récente → échec code 2 « plus récente » ; base illisible → échec code 2 sans modification du fichier ; dossier inutilisable → échec code 3 ; message des erreurs de service repris à l'identique, texte technique jamais dans le message ; hygiène : aucun fichier suivi de type base, DLL, modèle, média, archive, journal, secret ou chemin personnel (fichiers suivis uniquement, pas l'historique) ; aucune couleur codée en dur dans `ui/` hors jetons.

**E2 — démarrage de l'application (Qt)** · `python -m aniflow` et point d'entrée `aniflow` ; journal ; thème (style de base Fusion) ; logo en icône ; `--smoke-test` ; pont des messages Qt vers le journal ; `LC_NUMERIC=C`.
- Critères : fenêtre sombre fermée avec le code 0 en moins de 2 s ; aucun avertissement Qt (style compris) dans `aniflow.log` ; `--smoke-test` renvoie 0 ; base trop récente → dialogue lisible, code 2, aucune trace à l'écran ; `LC_NUMERIC` vaut `C`.

**E3 — fenêtre principale, navigation, persistance (Qt)** · barre latérale (logo, 6 entrées, version), pile de pages, états vides honnêtes.
- Critères : clic, Ctrl+1…6 et Tab/Entrée ouvrent la bonne page ; focus visible ; aucun bouton actif sur les pages non livrées ; redémarrage → même section et même géométrie, géométrie invalide ignorée ; taille minimale 960×600, lisible à 1920×1080 et 1366×768.

**E4 — icônes vectorielles (Lucide)** · SVG recolorés selon le thème, nets à 100/125/150 %, données dans le paquet, `THIRD_PARTY_NOTICES.md`.
- Critères : chaque icône référencée a son fichier ; SVG valides en 24×24 sans couleur codée en dur ; rendu non vide à 16/24/32 px et aux ratios 1,0/1,5/2,0 ; licence consignée ; logo lisible à 16/24/32/48 px (sinon variante simplifiée à décider).

**E5 — composants et états (Qt)** · carte, en-tête de section, états vide, chargement et erreur.
- Critères : l'état erreur affiche exactement le message utilisateur ; « Réessayer » appelle la fonction une fois par clic ; « Copier les détails » copie le texte technique (masqué par défaut) ; noms accessibles ; nouveaux jetons ≥ 4,5:1 (texte) et ≥ 3:1 (éléments).

**E6 — tâches en arrière-plan et erreurs (Qt)** · exécuteur hors fil d'interface, crochet d'exceptions global, arrêt propre.
- Critères : interface réactive pendant une tâche (minuteur de 20 ms ≥ 10 battements en 300 ms) ; succès traité dans le fil d'interface ; erreur de service → message français exact ; exception inconnue → message générique + trace au journal ; une exception dans un slot ne ferme pas l'application ; fermeture avec tâche en cours en 5 s au plus ; une connexion SQLite par fil.

**E7 — page Paramètres « Données et diagnostic » (Qt)** · version, dossiers de données et de journaux (« Ouvrir »), version du schéma, nombre de sauvegardes, « Créer une sauvegarde », langue des titres.
- Critères : chemins = ceux d'`AppPaths` ; « Créer une sauvegarde » ajoute exactement 1 fichier valide, état de chargement visible, échec simulé → erreur française ; langue des titres persistée ; aucune donnée personnelle autre que des chemins dans le journal. Restauration non incluse (phase 7).

**E8 — finitions, validation guidée, clôture (Qt)** · barre de titre sombre (méthode à vérifier dans la documentation de PySide6 6.12.0), navigation 100 % clavier, `docs/phase1/validation-windows.md`.
- Critères : barre de titre sombre avec repli sans exception ; 6 sections et Paramètres atteignables au clavier seul, noms accessibles ; captures à 1920×1080, 1366×768 et 2560×1440 pour 100/125/150 % sans troncature ; suite complète verte sur le PC de l'utilisateur ; tag de fin de phase.

## Tests

- **Purs** (exécutés par l'assistant, puis par l'utilisateur) : navigation, paramètres, démarrage, erreurs, hygiène, couleurs, icônes (recoloration, inventaire), contrastes.
- **Qt hors écran** (`tests/ui/*`, exécutés par l'utilisateur seul) : `QT_QPA_PLATFORM=offscreen` par défaut (`minimal` en repli), un `QApplication` partagé, ignorés si PySide6 est absent.
- **Visuels** : checklist de l'étape E8.

## Risques

1. Interface non exécutable par l'assistant : étapes petites, widgets minces, sorties collées.
2. QSS sans validation (les erreurs ne sont que des avertissements) : pont des messages Qt vers le journal + test.
3. Threads : une connexion SQLite par fil, exceptions avalées par les exécuteurs, fermeture avec tâches en cours.
4. Barre de titre claire sur application sombre : la méthode dépend de la version de Qt ; pas de fenêtre sans cadre.
5. Haute densité et polices : échelles 125/150 %, logo à petite taille.
6. Interface « finie » mais vide : règle de non-boutons-factices, testée.
7. Dépôt public : ne jamais committer base, rapports, DLL, modèles, vidéos, archives, secrets ni chemins personnels (garde-fou E1).
8. Paramètres régionaux et libmpv : Qt peut modifier `LC_NUMERIC` (verrouillé en E2, utile en phase 3).
9. Ressources lues depuis le dépôt (mode éditable) ; empaquetage en phase 7.
10. Licence du code source non choisie : non bloquant pour la phase 1.

## Fichiers

- Existants à modifier : `pyproject.toml` (E2, E4), `src/aniflow/database/settings.py` (E1), `src/aniflow/ui/theme/tokens.py` et `qss.py` (E3 à E5), `src/aniflow/paths.py` (E4), `tests/__init__.py` (E2), `tests/test_database.py` (E1), `tests/test_theme_paths_logging.py` (E5), documents de suivi.
- Nouveaux : `src/aniflow/{__main__,app,startup}.py`, `src/aniflow/ui/{navigation,errors,icons,main_window,sidebar,workers,qt_logging}.py`, `src/aniflow/ui/pages/*`, `src/aniflow/ui/components/*`, `src/aniflow/ui/assets/icons/*.svg`, tests purs et `tests/ui/*`, `tests/support/qt.py`, `docs/phase1/validation-windows.md`, `THIRD_PARTY_NOTICES.md`.

## Hors périmètre de la phase 1

Recherche et fiches (phase 2), bibliothèque et lecteur (phase 3), statistiques (phase 4), téléchargements (phase 5), IA locale dans l'interface (phase 6), restauration de sauvegarde et empaquetage (phase 7).
