# AniFlow — décisions d'architecture

## Décisions retenues

| Sujet | Décision | Motif / condition |
|---|---|---|
| Plateforme | Windows 11 | Cible principale. |
| Interface | Python + PySide6 | Application de bureau modulable. |
| Design | Sombre, bleu marine très foncé, moderne et minimaliste | Identité obligatoire, avec accents bleus et surfaces lisibles. |
| Logo | `docs/branding/aniflow-logo-final.png` approuvé | Torii blanc + livre/bibliothèque + bouton play bleu ; ne pas choisir d’autre concept sans demande. |
| Base de données | SQLite | Persistance locale sans serveur. |
| Métadonnées | AniList GraphQL au départ | Recherche, fiches et relations ; cache et fournisseurs extensibles. |
| Ordre par défaut | Chronologie complète | Tous les contenus connus, récapitulatifs inclus ; glisser-déposer si l'ordre est incertain. |
| Lecteur | MPV/libmpv à prototyper | Contrôle et progression, intégration Windows à valider. |
| IA | IA locale exclusive dès qu'elle est utilisée, avec Ollama comme premier runtime | Aucun endpoint IA cloud ni basculement distant. Si indisponible, la fonction IA signale l'erreur ; les fonctions indépendantes restent utilisables. |
| Téléchargements | Adaptateurs par source compatible + URLs directes supportées | Aucune garantie pour une page arbitraire ; pas de contournement de DRM ou d'accès restreint. |
| Suivi projet | GitHub + `PROJECT_STATUS.md` | Git conserve l'historique ; le fichier fournit à Claude une reprise concise. |
| Développement | Phases successives vers le périmètre complet | Chaque phase est testée, sans réduire l'objectif à un prototype jetable. |
| Client HTTP | Bibliothèque standard (`urllib`) derrière une interface `HttpTransport` ; aucune dépendance réseau tierce | Zéro dépendance, remplaçable ; redirections jamais suivies ; proxys système ignorés pour l'IA locale. *(phase 0)* |
| Débit AniList | 30 requêtes/min par défaut, espacement minimal 0,5 s, pénalité partagée après un 429, cache TTL (6 h recherche, 7 j fiches) ; 90/min reste la valeur nominale | La documentation officielle signale un mode dégradé à 30/min avec limiteur de rafale ; **confirmé en direct le 25/10/2026** (`X-RateLimit-Limit: 30`). À re-vérifier périodiquement. |
| Relations AniList | Lecture par lots `Page.media(id_in: [...])`, jusqu'à 50 fiches par requête | Une exploration récursive fiche par fiche saturerait 30 requêtes/min. |
| Contenu adulte | Recherche : `isAdult:false` par défaut (réglage `anilist.include_adult`) ; exploration des relations : jamais filtrée, étiquette `is_adult` conservée | Cohérent avec « ne rien masquer silencieusement » (SPEC §3.1). |
| Garde-fous IA locale | Adresse de bouclage uniquement ; modèles `-cloud` et entrées `remote_host`/`remote_model` refusés avant tout appel ; aucune redirection ; capacités lues via `/api/show` (échec fermé si inconnues) ; aucun `/api/pull` | Ollama exécute des modèles « cloud » via son API locale : une adresse locale ne garantit pas une inférence locale. Précise SPEC §9 et critère 12 (SPEC non modifié : ajout proposé). |
| Adresse IA locale | Liste blanche explicite et forme canonique : `localhost`, IPv4 décimale pointée stricte dans `127.0.0.0/8`, `::1` ; tout le reste refusé (IPv4-mappée ou compatible, NAT64/6to4, zone IPv6, décimal/hexadécimal/octal/abrégé, point final, noms DNS) ; le client se connecte à la forme canonique ; jamais `ipaddress.is_loopback` | La sémantique de `is_loopback` pour `::ffff:127.0.0.1` varie selon les correctifs de CPython (échec constaté sous 3.12.10, absent sous 3.12.3). `localhost` reste accepté tel quel (résolu par l'OS) ; le défaut est `127.0.0.1`. *(correctifs 1)* |
| Sortie des scripts | UTF-8 imposé sur stdout/stderr par `tools/phase0/_common.py` (tous les scripts) ; les tests capturent des octets, décodent strictement dans le thread du test et simulent une console Windows (`PYTHONIOENCODING=cp1252`) pour tous les sous-processus | Un tube Windows hérite de cp1252 ; avec `text=True`, une erreur de décodage dans le thread de lecture ne faisait pas échouer le test. *(correctifs 1)* |
| Serveur HTTP de test | Déconnexion du client tolérée seulement si déclarée (`tolerate_client_abort=True`) et comptée ; toute autre exception ou déconnexion non déclarée fait échouer le test ; les réponses en cours sont attendues à la sortie | Sous Windows un client qui coupe produit `ConnectionAbortedError` (WinError 10053), pas `BrokenPipeError` : l'ancien serveur ne traitait que deux types et ne laissait qu'une trace sur stderr. *(correctifs 1)* |
| Visibilité du dépôt | Public, choix explicite de l'utilisateur (26/10/2026) | Le code est visible ; aucune licence choisie (droits réservés par défaut). Ne jamais committer base, rapports, DLL, modèles, vidéos, archives, secrets ni chemins personnels : garde-fou automatisé sur les fichiers suivis (`tests/test_repo_hygiene.py`, étape E1). L'historique n'est volontairement pas audité. |
| Distribution et licence | Usage personnel uniquement ; aucun binaire avant décision explicite de licence ; licence du code source reportée | Confirmé par l'utilisateur le 26/10/2026. GPL/LGPL (libmpv, Qt, FFmpeg) à trancher avant toute diffusion. |
| Flux Git | `main` = états validés ; `phase0-integration` fusionnée dans `main` puis tag `phase0-validee` ; travail de la phase 1 sur la branche `phase1` | Décidé le 26/10/2026 ; commandes exécutées par l'utilisateur (l'assistant n'a aucun accès en écriture). |
| Versions et icônes | PySide6 6.12.0 (installée) ; icônes Lucide avec conservation des avis de licence (licence à re-vérifier à l'étape E4) | Choix de l'utilisateur (26/10/2026). La version de PySide6 conditionne l'API de la barre de titre sombre (à vérifier dans la documentation de 6.12.0, étape E8). |
| Restauration (interface) | Reportée à la phase 7 | Exige un redémarrage de l'application ; la fonction de restauration existe déjà au niveau service. |
| Périmètre de la phase 1 | Plan E0–E8 approuvé (`docs/phase1/PLAN.md`) : fenêtre principale, navigation, composants, tests, page Paramètres minimale | Décidé le 26/10/2026. |
| Navigation (E1) | 6 sections de SPEC §11 ; identifiants persistés `accueil`, `recherche`, `bibliotheque`, `telechargements`, `statistiques`, `parametres` (jamais renommés sans migration) ; raccourcis Ctrl+1…6 | Un test compare aussi les libellés à la ligne de SPEC §11. Paramètres `ui.last_section` et `ui.window_geometry` (base64 d'au plus 4096 octets) validés à l'écriture. |
| Démarrage et erreurs (E1) | `run_startup_checks` ne lève jamais : `StartupContext` ou `StartupFailure` (message français, code de sortie 1 inattendu, 2 base de données, 3 dossier de données) ; `describe_exception` reprend le `user_message` des services et n'affiche jamais de texte technique | Le détail technique va au journal, jamais à l'écran. |
| Modèle IA local | E2B et E4B restent candidats ; aucun choix avant un benchmark représentatif (phase 6) ; 12B non testé | Les mesures de la phase 0 (génération de 7 jetons) prouvent le fonctionnement, pas la qualité ni les performances. *(25/10/2026)* |
| Mesure de la mémoire IA | `nvidia-smi` et Gestionnaire des tâches pendant une charge réelle ; `/api/ps` seulement comme indice | Valeurs `/api/ps` incohérentes : 0,32 et 0,34 Go pour des modèles de 4,59 et 6,58 Go sur disque. *(25/10/2026)* |
| Build libmpv de référence | `mpv v0.41.0-1227-ge471496c5` / FFmpeg `N-127893-g9a861e968` (build git non officielle), à épingler pour la phase 3 ; toute autre build : relancer `mpv_probe.py` | Validée sous Windows le 25/10/2026 (7/7 en headless et en fenêtre). Variante de licence (GPL ou LGPL) non précisée par le rapport. |
| Pagination AniList | Se fier à `pageInfo.hasNextPage` ; ne pas afficher `total` comme nombre de résultats | `total` = 5000 observé pour une recherche simple : plafond probable. *(25/10/2026)* |
| Persistance | SQLite en WAL ; migrations numérotées (`PRAGMA user_version`) atomiques, précédées d'une sauvegarde ; refus d'ouvrir une base plus récente ; aucune suppression automatique de sauvegarde | SPEC §13 et règle « jamais d'effacement sans action explicite ». |
| Tests | `unittest` (bibliothèque standard, compatible pytest) ; serveurs HTTP locaux pour le vrai transport ; faux lecteur à horloge simulée | La suite ne dépend ni d'Internet ni de pytest. |
| `.gitignore` | Motifs de dossiers ancrés à la racine (`/Downloads/`, `/models/`, `/media/`…) | Le fichier recommandé ignorait, sous Windows (Git insensible à la casse), le futur paquet `src/aniflow/services/downloads/`. |

## Faits vérifiés en phase 0 (24 octobre 2026)

**AniList** — documentation officielle (docs.anilist.co)
- Limite : 90 requêtes/min nominales, mais l'API est « dégradée » à 30/min (non reflété dans les en-têtes) ; dépassement = pause d'1 min avec `Retry-After` ; limiteur de rafale en plus (`/guide/rate-limiting`).
- CGU (`/guide/terms-of-use`) : gratuit en non commercial ; interdits : usage comme sauvegarde/stockage de données, collecte massive, services concurrents non complémentaires. Conséquences : cache borné par TTL, aucun miroir de la base, **pas de binaire ni de service hébergé avant d'avoir clarifié la clause « services concurrents »** (usage personnel ; le dépôt public ne contient que du code source).
- `MediaRelation` : ADAPTATION, PREQUEL, SEQUEL, PARENT, SIDE_STORY, CHARACTER, **SUMMARY** (récapitulatif), ALTERNATIVE, SPIN_OFF, OTHER, et, avec `relationType(version: 2)`, SOURCE, COMPILATION, CONTAINS. `MediaFormat` : TV, TV_SHORT, MOVIE, SPECIAL, OVA, ONA, MUSIC, MANGA, NOVEL, ONE_SHOT. Une fiche inexistante renvoie HTTP 404.

**Ollama et Gemma 4**
- Les modèles cloud (suffixe `-cloud`) peuvent être appelés par `localhost:11434` mais s'exécutent chez Ollama ; `OLLAMA_NO_CLOUD=1` ou `disable_ollama_cloud` dans `~/.ollama/server.json` les désactive (docs.ollama.com/faq).
- Gemma 4 : tailles E2B, E4B, 12B, 26B A4B, 31B ; entrée audio native sur E2B, E4B et 12B seulement, **30 secondes maximum par entrée audio** ; la vidéo passe en images. Tags Ollama observés : `gemma4:e2b|e4b|12b|26b|31b`, variantes `-it-qat`, `-it-q4_K_M` (ollama.com/library/gemma4). Les tailles annoncées divergent selon les sources : **à mesurer** (`/api/tags`, `/api/ps`).
- La page Ollama liste « audio » parmi les capacités de la famille, mais rien ne prouve que chaque tag l'expose via l'API : le client lit `capabilities` dans `/api/show` (champ confirmé par plusieurs SDK tiers, à confirmer par la sonde sur la version installée) et refuse tout envoi audio/vidéo en attendant la phase 6.

**Lecteur**
- python-mpv : paquet PyPI `mpv` (≥ 1.0.8, Python ≥ 3.9), ctypes ; `libmpv-2.dll` doit être dans `%PATH%` ou à côté de `python.exe` (ordre de recherche de ctypes, pas celui de Windows) ; Qt perturbe la locale (`LC_NUMERIC` doit valoir `C`). Licence : celle de libmpv.
- DLL Windows non officielles : `mpv-dev-x86_64-*.7z` (shinchiro/mpv-winbuild-cmake, zhongfly/mpv-winbuild) ; la variante « v3 » exige un processeur récent ; `mpv-dev-lgpl-*.7z` = build LGPLv2.1+ (le mainteneur ne garantit pas l'absence de composants incompatibles).

**Détection d'intro (phase 6)** — AniSkip : `GET https://api.aniskip.com/v2/skip-times/{malId}/{épisode}?types[]=op&types[]=ed&types[]=mixed-op&types[]=mixed-ed&types[]=recap&episodeLength={s}` ; indexé par identifiant **MAL** (d'où `idMal` conservé dans nos modèles). Conditions d'usage non vérifiées.

## Mesuré sous Windows le 25 octobre 2026 (rapports JSON de l'utilisateur, Windows 11 10.0.22631, Python 3.12.10)

- **AniList :** en-tête `X-RateLimit-Limit: 30` ; 5 requêtes réseau → `remaining` 29 puis 25 (cohérent) ; lot `id_in` : 6 fiches en 1 requête ; 404 : « Not Found. » ; `pageInfo.total` = 5000.
- **libmpv :** `mpv v0.41.0-1227-ge471496c5`, FFmpeg `N-127893-g9a861e968` ; lecture, pause, ±15 s, seek absolu et reprise exacts à 0,01 s près ; en fenêtre, 2,68 s mesurés pour 3,0 s écoulés (dans la tolérance de 1,5 s, non investigué).
- **Ollama 0.40.8 :** `/api/show` renvoie `capabilities` ; `gemma4:e2b` = 4,59 Go, 4.6B, Q4_K_M ; `gemma4:e4b` = 6,58 Go, 7.5B, Q4_K_M ; contexte max 131072 ; capacités identiques : audio, completion, thinking, tools, vision ; `format` avec schéma JSON accepté.
- **Non interprétable :** débits et durées d'un test de 7 jetons (E2B mesuré en premier : démarrage à froid et cache disque, donc non comparable) ; `/api/ps` (0,32 / 0,34 Go).

## Dépendances et licences (état au 25 octobre 2026)

| Composant | Licence | Statut |
|---|---|---|
| Python | PSF | connu |
| PySide6 (Qt for Python) | édition communautaire LGPLv3/GPLv3, ou édition commerciale | vérifié le 25/10/2026 (doc.qt.io/qtforpython) ; en LGPL, privilégier une distribution en dossier (pas un exécutable unique) — à confirmer en phase 7 |
| python-mpv (`mpv`) | hérite de libmpv : GPLv2+ (défaut) ou LGPLv2.1+ | vérifié (README) |
| libmpv-2.dll (builds Windows) | GPL par défaut ; build LGPL séparée | vérifié (dépôts des builds) |
| FFmpeg / ffprobe | LGPL ou GPL selon la build | connu |
| Ollama | MIT | connu, non re-vérifié |
| Gemma 4 | Apache 2.0 | vérifié le 25/10/2026 (annonce officielle blog.google ; Gemma 3 et antérieurs relevaient des « Gemma Terms of Use ») |
| API AniList | CGU ci-dessus | vérifié |
| AniSkip ; extracteurs de téléchargement | — | non examinés (phases 5 et 6) |

**Distribution** : usage personnel uniquement (confirmé par l'utilisateur le 26/10/2026) ; aucun binaire distribué avant décision explicite de licence ; licence du code source reportée. Avant toute diffusion de binaires, choisir entre (A) AniFlow sous licence compatible GPL avec libmpv GPL, ou (B) libmpv LGPL + Qt LGPL en dossier + FFmpeg LGPL, puis faire valider (ceci n'est pas un avis juridique).

## Contradictions et précisions à valider

1. *(résolu le 26/10/2026)* Le dépôt existe et est **public par choix explicite de l'utilisateur** ; la consigne « dépôt privé » du kit initial est abandonnée. GitHub reste non lisible depuis l'environnement de développement (robots.txt) : la publication de `627a23d` sur `phase0-integration` est déclarée par l'utilisateur, non vérifiée directement.
2. SPEC §9 et critère 12 interdisent « tout service cloud », or Ollama peut en servir via son API locale : garde-fous ajoutés ; **ligne de SPEC à ajouter si vous validez** : « Les modèles Ollama cloud sont interdits au même titre que tout fournisseur distant. »
3. `.gitignore` recommandé : motifs non ancrés dangereux (voir tableau).
4. SPEC cite Gemma 4 12B : il existe, mais son empreinte (de l'ordre de 8 Go quantifié d'après une source secondaire) dépasse probablement la VRAM d'un GPU portable de classe RTX 2050 (≈ 4 Go, à confirmer par `nvidia-smi` : `/api/ps` indique la mémoire d'un modèle chargé, pas la capacité du GPU) : E2B/E4B sont les candidats réalistes ; décision après mesures.

## Points à vérifier pendant l’implémentation

- Première source de téléchargement compatible et autorisée pour un test d’intégration.
- Empaquetage Windows et licences des dépendances. *(licences recensées ci-dessus ; empaquetage : phase 7)*
- Modèle local et modalités réellement prises en charge par la version d’Ollama retenue. *(capacités et appels vérifiés sous Windows le 25/10/2026 ; qualité, performances et mémoire : benchmark représentatif en attente)*
- Source secondaire de métadonnées/chronologie capable de compléter AniList.
- Qualité des ressources de marque à différentes tailles ; le logo PNG fourni reste la référence approuvée.

Ces points sont des choix à décider au moment où ils deviennent nécessaires ; ils ne justifient pas de retarder les fonctionnalités indépendantes.
