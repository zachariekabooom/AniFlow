# AniFlow — roadmap de réalisation complète

Cette roadmap découpe le logiciel final en phases vérifiables. Ce n'est pas une réduction du périmètre : toutes les fonctionnalités de `SPEC.md` restent dans la cible. Une phase ne doit être cochée qu'après vérification réelle.

## Phase 0 — Cadrage, dépôt et preuves de faisabilité
- [ ] Lire `SPEC.md` v0.4 et intégrer `docs/branding/aniflow-logo-final.png` dans l’application.
- [ ] Créer un dépôt GitHub privé et committer le kit de planification.
- [ ] Valider une recherche AniList GraphQL.
- [ ] Prototyper MPV/libmpv : lecture, pause, seek, position de reprise sous Windows.
- [ ] Valider Ollama local + appels au modèle Gemma choisi ; aucun endpoint IA distant.
- [ ] Confirmer les dépendances, licences et choix de distribution.

## Phase 1 — Socle applicatif et design
- [ ] Structure Python/PySide6 modulaire, navigation et thème bleu marine sombre.
- [ ] Design tokens, typographie, cartes, composants, icônes et états de chargement/erreur.
- [ ] Configuration, journaux et erreurs compréhensibles.
- [ ] SQLite, migrations, persistance et sauvegarde/restauration.
- [ ] Tests ciblés de démarrage, navigation et persistance.

## Phase 2 — Recherche, métadonnées et chronologie
- [ ] Recherche et fiches AniList avec cache.
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
