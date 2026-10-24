# PROJECT_STATUS — AniFlow

> Fiche de reprise prioritaire. La maintenir courte, factuelle et à jour. Ne jamais en faire un résumé intégral de conversation.

- **Spécification :** `SPEC.md` v0.4
- **État :** cadrage finalisé, développement non commencé
- **Code applicatif :** aucun
- **Branche / commit stable :** dépôt GitHub à créer
- **Tests applicatifs :** aucun, car aucun code applicatif n'existe
- **Logo approuvé :** `docs/branding/aniflow-logo-final.png`
- **Prochaine action :** créer le dépôt GitHub selon `GITHUB_SETUP.md`, y déposer le kit, puis lancer `CLAUDE_MASTER_PROMPT.md` dans l'environnement Claude choisi.

## Décisions confirmées

- Windows 11, interface en français, design sombre moderne et minimaliste bleu marine très foncé avec accent bleu électrique.
- Logo final approuvé : torii blanc + livre/bibliothèque + bouton lecture bleu.
- AniList GraphQL pour la recherche et les métadonnées initiales, avec architecture extensible.
- Mode par défaut « Chronologie complète » incluant tous les contenus découverts, y compris récapitulatifs. Un glisser-déposer permet de réorganiser saisons, épisodes, films, OVA, spéciaux et récapitulatifs.
- Bibliothèque pour les animés en cours et déjà vus, avec ajout manuel des œuvres/fichiers, progression et compteur de re-visionnages extensible.
- Lecteur local intégré, reprise de progression, commandes ±15 s, chronomètre excluant les pauses et sauts de progression non réellement regardée.
- Gestionnaire de téléchargement persistant, dossiers et stockage configurables, reprise après redémarrage lorsque la source le permet, choix des saisons/épisodes/langues/qualités réellement disponibles.
- URL de source ou fichier local ajoutables manuellement ; les pages web arbitraires peuvent nécessiter un adaptateur compatible. Aucun contournement de DRM ou de contrôle d'accès.
- Toute fonction qui utilise de l'IA doit utiliser exclusivement une IA locale, via Ollama au départ. Aucun endpoint cloud/fallback distant. Si le modèle manque, afficher une erreur claire sans simulation ni bascule distante.
- Les statistiques doivent distinguer le temps mesuré par AniFlow des estimations historiques.
- L'application complète est construite en phases vers les exigences intégrales de `SPEC.md`, sans s'arrêter à un prototype jetable.

## Risques techniques à vérifier au cours du développement

- Exhaustivité et fiabilité des chronologies : aucune base unique ne garantit zéro oubli ; conserver les contenus incertains et autoriser leur correction.
- Compatibilité des URL de téléchargement : utiliser des sources accessibles et autorisées, des liens directs ou des adaptateurs dont la licence/maintenance a été vérifiée.
- Dépendances MPV/FFmpeg, empaquetage Windows et licences : les valider tôt.
- Capacités IA réelles : vérifier les modalités supportées par le couple exact Ollama/modèle. Ne pas envoyer audio/vidéo à un modèle qui ne sait pas les prendre en entrée.
- Machine cible à considérer pour les performances : Windows 11, 16 Go de RAM, MSI Thin GF63 12UCX et RTX 2050 déclarés par l'utilisateur ; mesurer plutôt que supposer.

## Protocole anti-perte de contexte et anti-gaspillage de tokens

### Début de session
1. Lire ce fichier en entier.
2. Lire seulement la phase courante dans `ROADMAP.md` et les sections pertinentes de `SPEC.md`.
3. Lire les décisions pertinentes de `DECISIONS.md` et les dernières entrées de `DEV_LOG.md`.
4. Inspecter `git status`, `git log -5 --oneline` et le diff pertinent si un dépôt existe.
5. Avant de coder, annoncer l'objectif en 5 à 10 lignes maximum, les fichiers ciblés et le test d'acceptation.

### Pendant la session
- Une seule phase/tâche principale à la fois, sans demander l'approbation de l'utilisateur entre chaque sous-tâche déjà prévue.
- Utiliser recherche ciblée, lecture de sections et `git diff`; ne jamais recopier le dépôt ou la conversation entière dans le contexte.
- Ne pas réécrire des modules stables sans raison vérifiée. Ne pas créer d'abstractions sans besoin.
- Avant de réutiliser une bibliothèque/projet existant, vérifier activité, licence, dépendances et conditions d'intégration, puis noter la décision.
- Ne jamais charger les vidéos, modèles IA, bases personnelles, caches ou secrets dans le contexte général.

### Fin de session ou checkpoint
1. Lancer uniquement les tests utiles au changement et rapporter les commandes + résultats exacts.
2. Indiquer les limites ou tests non réalisés (notamment ceux nécessitant Windows, accès externe ou matériel absent).
3. Examiner le diff et vérifier qu'aucun secret ou fichier local n'est ajouté.
4. Mettre à jour ce fichier et `ROADMAP.md`; ajouter un résumé concis à `DEV_LOG.md`; mettre à jour `DECISIONS.md` seulement si un choix change.
5. Indiquer une prochaine tâche unique et précise.
6. Commiter les changements cohérents testés si Git est configuré. Ne jamais force-push ni prétendre qu'un push a réussi sans l'avoir confirmé.

## Format de compte-rendu

- **Objectif :**
- **Fichiers modifiés :**
- **Tests exécutés et résultat :**
- **Non testé / blocages :**
- **Décisions changées :**
- **Prochaine tâche :**
- **Commit (si créé) :**
