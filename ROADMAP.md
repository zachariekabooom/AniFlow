# AniFlow — roadmap de réalisation complète

Cette roadmap découpe le logiciel final en phases vérifiables. Ce n'est pas une réduction du périmètre : toutes les fonctionnalités de `SPEC.md` restent dans la cible. Une phase ne doit être cochée qu'après vérification réelle.

Légende : `[x]` vérifié par un test exécuté (résultat dans `DEV_LOG.md`) · `[~]` code livré et testé en simulation ou sur serveur local, **validation réelle (Windows, réseau, matériel) en attente** · `[ ]` non fait.

## Phase 0 — Cadrage, dépôt et preuves de faisabilité
- [x] Lire `SPEC.md` v0.4.
- [~] Intégrer `docs/branding/aniflow-logo-final.png` dans l'application — chargeur (`aniflow.paths.logo_path`) et fenêtre de contrôle `qt_smoke.py` livrés ; affichage réel du PNG non vérifié (fichier et PySide6 absents de l'environnement de développement).
- [~] Dépôt GitHub privé et kit de planification — dépôt indiqué par l'utilisateur ; contenu/visibilité non vérifiables ici ; le code de la phase 0 est livré en archive à appliquer et committer.
- [~] Valider une recherche AniList GraphQL — client, limiteur, cache, erreurs et `anilist_probe.py` livrés (29 tests, dont 6 sur serveur HTTP local avec le vrai transport) ; **appel réel à AniList non testé** (réseau coupé).
- [~] Prototyper MPV/libmpv : lecture, pause, seek, position de reprise — logique de sonde testée avec un faux lecteur, `mpv_probe.py` et `qt_smoke.py` livrés ; **libmpv réel et Windows non testés**.
- [~] Valider Ollama local + appels au modèle Gemma choisi ; aucun endpoint IA distant — client à garde-fous (22 tests contre un faux Ollama local) et `ollama_probe.py` livrés ; **Ollama/Gemma réels non testés**.
- [~] Confirmer les dépendances, licences et choix de distribution — recensement sourcé dans `DECISIONS.md` ; choix de distribution (GPL ou LGPL) volontairement ouvert jusqu'à toute diffusion.

## Phase 1 — Socle applicatif et design
- [~] Structure Python/PySide6 modulaire, navigation et thème bleu marine sombre — paquet `src/aniflow`, jetons de design et feuille de style Qt livrés (contrastes WCAG testés) ; fenêtre principale et navigation non faites.
- [~] Design tokens, typographie, cartes, composants, icônes et états de chargement/erreur — jetons, typographie et styles de base faits ; composants, icônes et états non faits.
- [x] Configuration, journaux et erreurs compréhensibles — `SettingsStore` validé (IA locale imposée dès la configuration), journal tournant, erreurs françaises par service.
- [x] SQLite, migrations, persistance et sauvegarde/restauration — migrations atomiques avec sauvegarde préalable, restauration vérifiée avec copie de sécurité, cache HTTP persistant (19 tests).
- [~] Tests ciblés de démarrage, navigation et persistance — persistance testée ; démarrage et navigation de l'interface non faits.

## Phase 2 — Recherche, métadonnées et chronologie
- [ ] Recherche et fiches AniList avec cache. *(client et cache prêts ; reste l'intégration à l'interface et la persistance des œuvres)*
  - Note de conception vérifiée : l'API est limitée à 30 requêtes/min ; explorer les relations par lots `id_in` (50 fiches/requête) et mettre en cache, sans collecte massive (CGU).
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
- [ ] Vérifier pour le runtime/modèle local les modalités effectivement prises en charge.
- [ ] Proposer les plages avec niveau de confiance et permettre une correction manuelle.
- [ ] Tests sur intro raccourcie, absente, outro, récapitulatif et scène post-générique.

## Phase 7 — Finition, robustesse et distribution
- [ ] Revue des parcours critiques et tests de non-régression ciblés.
- [ ] Vérifier sauvegarde/restauration, chemins absents, disque plein et téléchargements incomplets.
- [ ] Vérifier les performances et consommation mémoire sur le PC cible.
- [ ] Tester l'installation sur un Windows 11 propre et documenter les dépendances.
- [ ] Documenter limites, licences, sources compatibles et modèle IA local.
- [ ] Tag et release v1.0 uniquement après satisfaction des critères de `SPEC.md`.
