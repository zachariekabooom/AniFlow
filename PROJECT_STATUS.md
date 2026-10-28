# PROJECT_STATUS — AniFlow

> Fiche de reprise prioritaire. La maintenir courte, factuelle et à jour. Ne jamais en faire un résumé intégral de conversation.

- **Spécification :** `SPEC.md` v0.4 (inchangée)
- **État :** **phase 0 terminée (26 oct. 2026)** : preuves réelles sous Windows 11 du 25 oct. 2026 (AniList, libmpv en headless et en fenêtre, Qt + logo, Ollama 0.40.8 avec Gemma 4 E2B et E4B) et confirmations explicites de l'utilisateur. **Phase 1 ouverte** : plan E0–E8 approuvé (`docs/phase1/PLAN.md`) ; E0 (documents) et E1 (logique pure) livrés dans `aniflow-phase1-e0-e1.zip`, **exécution de E1 sous Windows en attente** ; E2 à E8 non commencées.
- **Code applicatif :** `src/aniflow/` (clients AniList et Ollama local, base SQLite, thème, sonde libmpv ; depuis E1 : modèle de navigation, contrôles de démarrage, traduction des erreurs), sondes dans `tools/phase0/`, procédure Windows de la phase 0 dans `docs/phase0/validation-windows.md`. Aucune fenêtre applicative n'existe encore.
- **Dépôt :** https://github.com/zachariekabooom/AniFlow — **public (choix explicite de l'utilisateur)**. Commit `627a23d` poussé sur la branche `phase0-integration` (déclaré par l'utilisateur ; GitHub n'est pas lisible depuis l'environnement de développement, donc non vérifié directement). Code livré par archives ; l'assistant n'a aucun accès en écriture.
- **Dernier commit stable :** `627a23d` (branche `phase0-integration`, déclaré par l'utilisateur) ; fusion dans `main` et tag `phase0-validee` à exécuter par l'utilisateur.
- **Distribution et licence :** usage personnel uniquement ; aucun binaire distribué avant décision explicite de licence ; licence du code source reportée (tant qu'aucun fichier `LICENSE` n'existe, le code public est « tous droits réservés » par défaut).
- **Tests :** 165 tests `unittest` passent dans l'environnement de développement (Linux, Python 3.12.3, exécutés par l'assistant). Dernier résultat sous Windows 11 / Python 3.12.10 (communiqué par l'utilisateur, avant E1) : 123 exécutés, OK, 2 ignorés. **E1 non encore exécuté sous Windows.**
- **Preuves réelles sous Windows (25 oct. 2026, rapports JSON de l'utilisateur) :**
  - AniList : recherche, fiche avec relations, lecture par lot `id_in` (6 demandées / 6 reçues), erreur 404 propre, cache ; en-tête `X-RateLimit-Limit` = 30 (limite dégradée confirmée en direct).
  - libmpv `mpv v0.41.0-1227-ge471496c5` : 7 contrôles sur 7 en headless et en fenêtre (lecture, pause, ±15 s, seek absolu, reprise) ; intégration Qt : logo chargé, Lecture/Pause et ±15 s vérifiés visuellement par l'utilisateur.
  - Ollama 0.40.8 (`OLLAMA_NO_CLOUD=1` déclaré) : `gemma4:e2b` (4,59 Go) et `gemma4:e4b` (6,58 Go) prêts, capacités `audio/completion/thinking/tools/vision`, JSON structuré valide, aucun modèle distant.
- **Non testé / non conclu :** réponse 429 réelle d'AniList ; recherche avec `include_adult=True` en réel ; **envoi d'audio via Ollama** (capacité annoncée, mode d'envoi non vérifié) ; **qualité et performances des modèles** (aucun benchmark représentatif : des mesures sur 7 jetons ne permettent aucune conclusion) ; Gemma 4 12B ; empreinte mémoire des modèles (valeurs `/api/ps` incohérentes) ; rendu du thème Qt (non confirmé explicitement) ; exécution sous Windows des tests d'E1, dont le garde-fou d'hygiène sur les fichiers suivis du dépôt réel.
- **Logo approuvé :** `docs/branding/aniflow-logo-final.png` — chargé par Qt sous Windows (`logo_loaded: true`)
- **Prochaine action unique :** exécuter la livraison E0 + E1 sur le PC de l'utilisateur : commandes Git (fusion de `phase0-integration` dans `main`, tag `phase0-validee`, branche `phase1`), extraction de `aniflow-phase1-e0-e1.zip`, `python -m unittest discover -s tests -t .` et renvoi de la sortie complète ; E2 suivra.

## Décisions confirmées

- Windows 11, interface en français, design sombre moderne et minimaliste bleu marine très foncé avec accent bleu électrique.
- Logo final approuvé : torii blanc + livre/bibliothèque + bouton lecture bleu.
- AniList GraphQL pour la recherche et les métadonnées initiales, architecture extensible. Limite à respecter : 30 requêtes/min (confirmée en direct) → lectures par lots et cache ; se fier à `hasNextPage`, pas à `total`.
- Mode par défaut « Chronologie complète » incluant tous les contenus découverts, y compris récapitulatifs ; glisser-déposer pour réorganiser.
- Bibliothèque, lecteur local intégré (±15 s, reprise, chronomètre excluant pauses et sauts), gestionnaire de téléchargement persistant, statistiques distinguant mesuré et estimé — inchangés (voir `SPEC.md`).
- URL de source ou fichier local ajoutables manuellement ; aucun contournement de DRM ou de contrôle d'accès.
- IA exclusivement locale (Ollama d'abord) : adresse de bouclage seulement, **modèles Ollama « cloud » refusés**, aucun repli distant, aucune modalité envoyée sans capacité annoncée, aucun téléchargement de modèle automatique.
- **Modèle local : E2B et E4B restent candidats ; aucun choix avant un benchmark représentatif (phase 6) ; 12B non testé.**
- libmpv : build de référence validée `mpv v0.41.0-1227-ge471496c5` (build git non officielle), à épingler pour la phase 3.
- **Dépôt public voulu ; usage personnel ; aucun binaire avant décision explicite de licence ; licence du code source reportée (26/10/2026).**
- **Flux Git : `phase0-integration` fusionnée dans `main` + tag `phase0-validee`, puis branche `phase1`. PySide6 6.12.0. Icônes Lucide avec avis de licence. Restauration de sauvegarde (interface) reportée à la phase 7. Plan de la phase 1 approuvé.**
- Le logiciel complet est construit par phases vérifiables, sans s'arrêter à un prototype jetable.
- Tests en `unittest` (aucune dépendance) ; `.gitignore` corrigé : motifs ancrés à la racine.

## Risques techniques à vérifier au cours du développement

- Exhaustivité et fiabilité des chronologies : aucune base unique ne garantit zéro oubli ; conserver les contenus incertains et autoriser leur correction.
- Compatibilité des URL de téléchargement : sources autorisées, liens directs ou adaptateurs à licence et maintenance vérifiées.
- libmpv sous Windows : **prouvé** (7/7 headless et fenêtre) avec une build git non officielle ; restent : variante de licence de cette build (GPL ou LGPL non précisée), épinglage, empaquetage.
- IA : audio annoncé mais envoi non vérifié (limite de 30 s par entrée) ; empreinte mémoire inconnue (`/api/ps` : 0,32 et 0,34 Go, non interprétable) → mesurer avec `nvidia-smi` / Gestionnaire des tâches ; démarrage à froid observé de 21,6 à 56,7 s (l'interface devra être asynchrone) ; qualité et débit à mesurer sur tâches réelles.
- CGU AniList : pas de miroir de la base ; pas de binaire ni de service hébergé avant d'avoir clarifié la clause « services concurrents » (le dépôt public ne contient que du code source).
- Dépôt public : ne jamais committer base de données, rapports, DLL, modèles, vidéos, archives, secrets ni chemins personnels — garde-fou automatisé sur les fichiers suivis (E1).
- Phase 1 : l'assistant ne peut pas exécuter PySide6 ; toute étape d'interface est validée sur le PC de l'utilisateur.
- Machine cible : Windows 11, 16 Go de RAM, MSI Thin GF63 12UCX, RTX 2050 (déclaré par l'utilisateur) ; mesurer plutôt que supposer.

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
