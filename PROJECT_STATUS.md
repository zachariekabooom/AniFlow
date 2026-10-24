# PROJECT_STATUS — AniFlow

> Fiche de reprise prioritaire. La maintenir courte, factuelle et à jour. Ne jamais en faire un résumé intégral de conversation.

- **Spécification :** `SPEC.md` v0.4 (inchangée)
- **État :** phase 0 — code et sondes livrés, **validation sous Windows en attente** ; phase 1 — socle non graphique fait (SQLite, migrations, sauvegarde, paramètres, journaux, thème), interface non commencée
- **Code applicatif :** `src/aniflow/` (clients AniList et Ollama local, base SQLite, thème, sonde libmpv), sondes dans `tools/phase0/`, procédure dans `docs/phase0/validation-windows.md`
- **Dépôt :** https://github.com/zachariekabooom/AniFlow — non lisible depuis l'environnement de développement (robots.txt) ; **aucun accès en écriture** : le code est livré dans `aniflow-phase0.zip`, à extraire à la racine du dépôt puis à committer
- **Dernier commit stable :** aucun (rien n'a été poussé)
- **Tests :** 113 tests `unittest` passent (`python -m unittest discover -s tests -t .`), sans Internet ni PySide6
- **Non testé :** AniList réel, libmpv et lecture sous Windows, Qt/PySide6 et affichage du logo, Ollama et Gemma réels
- **Logo approuvé :** `docs/branding/aniflow-logo-final.png` (non vu par le développement : absent de l'environnement)
- **Prochaine action unique :** suivre `docs/phase0/validation-windows.md` (étapes 1 à 5) et renvoyer les rapports JSON de `reports/` ; la phase 0 ne sera cochée qu'après leur lecture.

## Décisions confirmées

- Windows 11, interface en français, design sombre moderne et minimaliste bleu marine très foncé avec accent bleu électrique.
- Logo final approuvé : torii blanc + livre/bibliothèque + bouton lecture bleu.
- AniList GraphQL pour la recherche et les métadonnées initiales, architecture extensible. Limite à respecter : 30 requêtes/min (mode dégradé documenté) → lectures par lots et cache.
- Mode par défaut « Chronologie complète » incluant tous les contenus découverts, y compris récapitulatifs ; glisser-déposer pour réorganiser.
- Bibliothèque, lecteur local intégré (±15 s, reprise, chronomètre excluant pauses et sauts), gestionnaire de téléchargement persistant, statistiques distinguant mesuré et estimé — inchangés (voir `SPEC.md`).
- URL de source ou fichier local ajoutables manuellement ; aucun contournement de DRM ou de contrôle d'accès.
- IA exclusivement locale (Ollama d'abord) : adresse de bouclage seulement, **modèles Ollama « cloud » refusés**, aucun repli distant, aucune modalité envoyée sans capacité annoncée, aucun téléchargement de modèle automatique.
- Le logiciel complet est construit par phases vérifiables, sans s'arrêter à un prototype jetable.
- Tests en `unittest` (aucune dépendance) ; `.gitignore` corrigé : motifs ancrés à la racine.

## Risques techniques à vérifier au cours du développement

- Exhaustivité et fiabilité des chronologies : aucune base unique ne garantit zéro oubli ; conserver les contenus incertains et autoriser leur correction.
- Compatibilité des URL de téléchargement : sources autorisées, liens directs ou adaptateurs à licence et maintenance vérifiées.
- libmpv sous Windows : DLL non officielle (GPL par défaut), recherche de DLL par ctypes, locale Qt — **à prouver par la sonde** ; licences et empaquetage à trancher avant toute diffusion.
- IA : audio Gemma 4 limité à 30 s par entrée et exposition par Ollama non prouvée pour chaque tag ; mémoire du GPU portable probablement serrée (≈ 4 Go à confirmer) → mesurer E2B, E4B puis 12B.
- CGU AniList : pas de miroir de la base, pas de diffusion publique avant d'avoir clarifié la clause « services concurrents ».
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
