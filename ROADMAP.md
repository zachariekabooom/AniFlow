# AniFlow — roadmap de réalisation complète

Cette roadmap découpe le logiciel final en phases vérifiables. Ce n'est pas une réduction du périmètre : toutes les fonctionnalités de `SPEC.md` restent dans la cible. Une phase ne doit être cochée qu'après vérification réelle.

Légende : `[x]` vérifié par un test exécuté (résultat dans `DEV_LOG.md`) · `[~]` code livré et testé en simulation ou sur serveur local, **validation réelle (Windows, réseau, matériel) en attente** · `[ ]` non fait.

## Phase 0 — Cadrage, dépôt et preuves de faisabilité
*Statut : **phase terminée le 26 octobre 2026** — 8 critères sur 8 : preuves réelles sous Windows 11 (rapports du 25 octobre 2026) et confirmations explicites de l'utilisateur (26 octobre 2026).*
- [x] Lire `SPEC.md` v0.4.
- [x] Intégrer `docs/branding/aniflow-logo-final.png` dans l'application — le PNG est chargé par Qt sous Windows (`qt.json` : `logo_loaded: true`) dans la fenêtre de contrôle ; fenêtre principale, icône d'application et variantes de taille relèvent de la phase 1.
- [x] Dépôt GitHub et kit de planification — dépôt **public, choix explicite de l'utilisateur** ; commit `627a23d` poussé sur la branche `phase0-integration` (déclaré par l'utilisateur ; GitHub n'est pas lisible depuis l'environnement de développement, donc non vérifié directement). Fusion dans `main`, tag `phase0-validee` et branche `phase1` : à exécuter par l'utilisateur (commandes dans `DEV_LOG.md`).
- [x] Valider une recherche AniList GraphQL — vérifié sous Windows le 25/10/2026 (`anilist.json`, 5 étapes sur 5) : recherche, fiche avec relations (`relationType(version: 2)`), lecture par lot `id_in` (6 demandées, 6 reçues), erreur 404 propre, cache (0,09 ms) ; `X-RateLimit-Limit` observé : 30. Non exercés en réel : réponse 429, recherche avec `include_adult=True`.
- [x] Prototyper MPV/libmpv : lecture, pause, seek, position de reprise sous Windows — vérifié (`mpv-headless.json` et `mpv-window.json` : 7 contrôles sur 7 dans chaque mode, build `mpv v0.41.0-1227-ge471496c5`) ; intégration dans une fenêtre Qt (`qt.json`) avec Lecture/Pause et ±15 s vérifiés visuellement par l'utilisateur.
- [x] Valider Ollama local + appels à Gemma ; aucun endpoint IA distant — vérifié sous Windows (`ollama-e2b.json`, `ollama-e4b.json`) : Ollama 0.40.8, `gemma4:e2b` et `gemma4:e4b` prêts, capacités annoncées `audio`, `completion`, `thinking`, `tools`, `vision`, JSON structuré valide, aucun modèle distant ; `OLLAMA_NO_CLOUD=1` déclaré par l'utilisateur. **Le choix du modèle n'est pas fait** : E2B et E4B restent candidats jusqu'au benchmark représentatif (phase 6) ; 12B non testé.
- [x] Confirmer les dépendances, licences et choix de distribution — dépendances confirmées à l'exécution (Python 3.12.10, PySide6, python-mpv + libmpv, Ollama) ; licences recensées et vérifiées dans `DECISIONS.md` (Gemma 4 : Apache 2.0 ; PySide6 : LGPLv3/GPLv3 ou commerciale) ; **décision de distribution confirmée par l'utilisateur le 26/10/2026** : usage personnel uniquement, aucun binaire distribué avant décision explicite de licence ; licence du code source reportée.
- [x] Suite de tests sous Windows 11 / Python 3.12.10 — 123 tests exécutés, OK, 2 ignorés (résultat communiqué par l'utilisateur, sortie complète non jointe) ; les trois défauts de la première exécution (adresse IPv4-mappée, décodage 0xE9, WinError 10053) ont été corrigés par les correctifs 1.

## Phase 1 — Socle applicatif et design
- [~] Structure Python/PySide6 modulaire, navigation et thème bleu marine sombre — paquet `src/aniflow`, jetons de design et feuille de style Qt livrés (contrastes WCAG testés) ; (E1) modèle de navigation pur livré et testé sous Linux ; fenêtre principale et navigation graphique non faites.
- [~] Design tokens, typographie, cartes, composants, icônes et états de chargement/erreur — jetons, typographie et styles de base faits ; composants, icônes et états non faits.
- [x] Configuration, journaux et erreurs compréhensibles — `SettingsStore` validé (IA locale imposée dès la configuration), journal tournant, erreurs françaises par service.
- [x] SQLite, migrations, persistance et sauvegarde/restauration — migrations atomiques avec sauvegarde préalable, restauration vérifiée avec copie de sécurité, cache HTTP persistant (19 tests).
- [~] Tests ciblés de démarrage, navigation et persistance — persistance testée ; (E1) logique de navigation, de démarrage et de mémorisation section/géométrie testée sans Qt sous Linux ; démarrage graphique et navigation de l'interface non faits.

Plan détaillé approuvé le 26/10/2026 : `docs/phase1/PLAN.md` (étapes E0 à E8). Un `[x]` n'est posé que sur résultat communiqué par l'utilisateur lorsqu'il dépend de son PC.
- [~] E0 — clôture documentaire de la phase 0 : documents livrés ; reste à exécuter par l'utilisateur : fusion de `phase0-integration` dans `main`, tag `phase0-validee`, branche `phase1`.
- [~] E1 — logique pure et garde-fous : code et tests livrés, exécutés sous Linux par l'assistant ; exécution sous Windows en attente.
- [ ] E2 — démarrage de l'application (première fenêtre, thème, journal).
- [ ] E3 — fenêtre principale, navigation, persistance.
- [ ] E4 — icônes vectorielles (Lucide).
- [ ] E5 — composants et états.
- [ ] E6 — tâches en arrière-plan et erreurs.
- [ ] E7 — page Paramètres « Données et diagnostic ».
- [ ] E8 — finitions, validation guidée, clôture.

## Phase 2 — Recherche, métadonnées et chronologie
- [ ] Recherche et fiches AniList avec cache. *(client et cache prêts ; reste l'intégration à l'interface et la persistance des œuvres)*
  - Note de conception confirmée sous Windows (25/10/2026) : l'en-tête `X-RateLimit-Limit` vaut 30 ; la lecture par lots `id_in` fonctionne (6 fiches en 1 requête) — explorer les relations par lots et mettre en cache, sans collecte massive (CGU) ; `pageInfo.total` vaut 5000 (plafond probable) → se fier à `hasNextPage` ; relations observées pour *Sousou no Frieren* : SOURCE, CHARACTER, SIDE_STORY ×2, OTHER, SEQUEL.
- [ ] Explorer récursivement les relations entre œuvres et consulter d'autres sources identifiées si nécessaire.
- [ ] Construire la liste par éléments individuels (épisodes) et unités (films, OVA, spéciaux).
- [ ] Le mode par défaut inclut tous les contenus connus, dont les récapitulatifs.
- [ ] Modes Chronologie complète, Histoire principale, Ordre de sortie et Liste intégrale.
- [ ] Glisser-déposer de tous les éléments, y compris insertion d'un film au milieu d'une saison.
- [ ] Marquage des incertitudes, verrouillage de placement et conservation des corrections.
- [ ] Tests sur franchises de démonstration à structure complexe.

## Phase 3 — Bibliothèque, import manuel et lecteur
- [ ] Bibliothèque, statuts de visionnage répété et compteur extensible.
- [ ] Ajout manuel d'animés déjà regardés et sélection de leur contenu vu.
- [ ] Import de dossiers et ajout manuel d'un fichier précis à un épisode.
- [ ] Lecteur MPV intégré, commandes ±15 s, sous-titres/audio et plein écran si disponibles.
- [ ] Bouton Suivant suivant la file personnalisée et reprise de progression.
- [ ] Chronomètre basé sur les périodes de lecture réelles, pause exclue.

## Phase 4 — Historique et statistiques
- [ ] Historique de sessions et calcul du temps mesuré.
- [ ] Distinction entre historique estimé et temps réellement suivi.
- [ ] Onglet Statistiques avec graphiques, genres/tags, temps et nombres de contenus.
- [ ] Dénominateurs et définitions affichés ; possibilité de corriger l'historique.
- [ ] Tests des calculs et de la restauration après redémarrage.

## Phase 5 — Téléchargements et espace de stockage
- [ ] File persistante, états et reprises après redémarrage.
- [ ] Dossier de destination, taille occupée, espace libre et gestion des fichiers temporaires.
- [ ] Choix de saison/épisodes, langue et qualité réellement disponibles.
- [ ] Enregistrement d'une URL par œuvre/épisode, liens média directs et adaptateur de première source compatible.
- [ ] Ajout manuel de média local lorsque l'autodétection échoue.
- [ ] Tests de pause/reprise, d'erreur, de doublon et de fichier partiel.

## Phase 6 — Détection des intros/outros et IA locale exclusive
- [ ] Recherche de timestamps via une source communautaire lorsqu'une entrée existe.
- [ ] Empreintes audio et/ou similitudes visuelles sur les épisodes locaux.
- [ ] Ollama local obligatoire pour les sous-tâches qui nécessitent de l'IA ; jamais d'appel distant ni de fallback cloud.
- [ ] Vérifier pour le runtime/modèle local les modalités effectivement prises en charge. *(constat sous Windows : Ollama 0.40.8 annonce `audio` pour `gemma4:e2b` et `gemma4:e4b` ; mode d'envoi de l'audio via l'API non vérifié, limite de 30 s par entrée ; le client refuse l'audio tant qu'il n'est pas validé)*
- [ ] Benchmark représentatif des modèles candidats (E2B, E4B ; 12B si la mémoire le permet) **avant tout choix** : tâches réelles du produit, qualité mesurée sur un jeu annoté, débit sur entrées réalistes, latence à froid et à chaud (21,6 à 56,7 s observés au premier chargement), mémoire GPU/RAM mesurée avec `nvidia-smi` / Gestionnaire des tâches (les valeurs `/api/ps` observées sont incohérentes), `total_duration` journalisé.
- [ ] Proposer les plages avec niveau de confiance et permettre une correction manuelle.
- [ ] Tests sur intro raccourcie, absente, outro, récapitulatif et scène post-générique.

## Phase 7 — Finition, robustesse et distribution
- [ ] Revue des parcours critiques et tests de non-régression ciblés.
- [ ] Vérifier sauvegarde/restauration, chemins absents, disque plein et téléchargements incomplets.
- [ ] Vérifier les performances et consommation mémoire sur le PC cible.
- [ ] Tester l'installation sur un Windows 11 propre et documenter les dépendances.
- [ ] Documenter limites, licences, sources compatibles et modèle IA local.
- [ ] Tag et release v1.0 uniquement après satisfaction des critères de `SPEC.md`.
