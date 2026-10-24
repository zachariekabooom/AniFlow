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
| Débit AniList | 30 requêtes/min par défaut, espacement minimal 0,5 s, pénalité partagée après un 429, cache TTL (6 h recherche, 7 j fiches) ; 90/min reste la valeur nominale | La documentation officielle signale un mode dégradé à 30/min avec limiteur de rafale. À re-vérifier. |
| Relations AniList | Lecture par lots `Page.media(id_in: [...])`, jusqu'à 50 fiches par requête | Une exploration récursive fiche par fiche saturerait 30 requêtes/min. |
| Contenu adulte | Recherche : `isAdult:false` par défaut (réglage `anilist.include_adult`) ; exploration des relations : jamais filtrée, étiquette `is_adult` conservée | Cohérent avec « ne rien masquer silencieusement » (SPEC §3.1). |
| Garde-fous IA locale | Adresse de bouclage uniquement ; modèles `-cloud` et entrées `remote_host`/`remote_model` refusés avant tout appel ; aucune redirection ; capacités lues via `/api/show` (échec fermé si inconnues) ; aucun `/api/pull` | Ollama exécute des modèles « cloud » via son API locale : une adresse locale ne garantit pas une inférence locale. Précise SPEC §9 et critère 12 (SPEC non modifié : ajout proposé). |
| Persistance | SQLite en WAL ; migrations numérotées (`PRAGMA user_version`) atomiques, précédées d'une sauvegarde ; refus d'ouvrir une base plus récente ; aucune suppression automatique de sauvegarde | SPEC §13 et règle « jamais d'effacement sans action explicite ». |
| Tests | `unittest` (bibliothèque standard, compatible pytest) ; serveurs HTTP locaux pour le vrai transport ; faux lecteur à horloge simulée | La suite ne dépend ni d'Internet ni de pytest. |
| `.gitignore` | Motifs de dossiers ancrés à la racine (`/Downloads/`, `/models/`, `/media/`…) | Le fichier recommandé ignorait, sous Windows (Git insensible à la casse), le futur paquet `src/aniflow/services/downloads/`. |

## Faits vérifiés en phase 0 (24 octobre 2026)

**AniList** — documentation officielle (docs.anilist.co)
- Limite : 90 requêtes/min nominales, mais l'API est « dégradée » à 30/min (non reflété dans les en-têtes) ; dépassement = pause d'1 min avec `Retry-After` ; limiteur de rafale en plus (`/guide/rate-limiting`).
- CGU (`/guide/terms-of-use`) : gratuit en non commercial ; interdits : usage comme sauvegarde/stockage de données, collecte massive, services concurrents non complémentaires. Conséquences : cache borné par TTL, aucun miroir de la base, **pas de diffusion publique avant d'avoir clarifié la clause « services concurrents »** (usage privé actuel sans objet).
- `MediaRelation` : ADAPTATION, PREQUEL, SEQUEL, PARENT, SIDE_STORY, CHARACTER, **SUMMARY** (récapitulatif), ALTERNATIVE, SPIN_OFF, OTHER, et, avec `relationType(version: 2)`, SOURCE, COMPILATION, CONTAINS. `MediaFormat` : TV, TV_SHORT, MOVIE, SPECIAL, OVA, ONA, MUSIC, MANGA, NOVEL, ONE_SHOT. Une fiche inexistante renvoie HTTP 404.

**Ollama et Gemma 4**
- Les modèles cloud (suffixe `-cloud`) peuvent être appelés par `localhost:11434` mais s'exécutent chez Ollama ; `OLLAMA_NO_CLOUD=1` ou `disable_ollama_cloud` dans `~/.ollama/server.json` les désactive (docs.ollama.com/faq).
- Gemma 4 : tailles E2B, E4B, 12B, 26B A4B, 31B ; entrée audio native sur E2B, E4B et 12B seulement, **30 secondes maximum par entrée audio** ; la vidéo passe en images. Tags Ollama observés : `gemma4:e2b|e4b|12b|26b|31b`, variantes `-it-qat`, `-it-q4_K_M` (ollama.com/library/gemma4). Les tailles annoncées divergent selon les sources : **à mesurer** (`/api/tags`, `/api/ps`).
- La page Ollama liste « audio » parmi les capacités de la famille, mais rien ne prouve que chaque tag l'expose via l'API : le client lit `capabilities` dans `/api/show` (champ confirmé par plusieurs SDK tiers, à confirmer par la sonde sur la version installée) et refuse tout envoi audio/vidéo en attendant la phase 6.

**Lecteur**
- python-mpv : paquet PyPI `mpv` (≥ 1.0.8, Python ≥ 3.9), ctypes ; `libmpv-2.dll` doit être dans `%PATH%` ou à côté de `python.exe` (ordre de recherche de ctypes, pas celui de Windows) ; Qt perturbe la locale (`LC_NUMERIC` doit valoir `C`). Licence : celle de libmpv.
- DLL Windows non officielles : `mpv-dev-x86_64-*.7z` (shinchiro/mpv-winbuild-cmake, zhongfly/mpv-winbuild) ; la variante « v3 » exige un processeur récent ; `mpv-dev-lgpl-*.7z` = build LGPLv2.1+ (le mainteneur ne garantit pas l'absence de composants incompatibles).

**Détection d'intro (phase 6)** — AniSkip : `GET https://api.aniskip.com/v2/skip-times/{malId}/{épisode}?types[]=op&types[]=ed&types[]=mixed-op&types[]=mixed-ed&types[]=recap&episodeLength={s}` ; indexé par identifiant **MAL** (d'où `idMal` conservé dans nos modèles). Conditions d'usage non vérifiées.

## Dépendances et licences (état au 24 octobre 2026)

| Composant | Licence | Statut |
|---|---|---|
| Python | PSF | connu |
| PySide6 (Qt for Python) | LGPLv3 / GPL / commerciale | connu, non re-vérifié ; en LGPL, privilégier une distribution en dossier (pas un exécutable unique) — à confirmer en phase 7 |
| python-mpv (`mpv`) | hérite de libmpv : GPLv2+ (défaut) ou LGPLv2.1+ | vérifié (README) |
| libmpv-2.dll (builds Windows) | GPL par défaut ; build LGPL séparée | vérifié (dépôts des builds) |
| FFmpeg / ffprobe | LGPL ou GPL selon la build | connu |
| Ollama | MIT | connu, non re-vérifié |
| Gemma 4 | conditions propres au modèle | **non vérifié** : lire avant le premier usage durable |
| API AniList | CGU ci-dessus | vérifié |
| AniSkip ; extracteurs de téléchargement | — | non examinés (phases 5 et 6) |

**Distribution** : en usage personnel (dépôt privé), aucune obligation de redistribution. Avant toute diffusion de binaires, choisir entre (A) AniFlow sous licence compatible GPL avec libmpv GPL, ou (B) libmpv LGPL + Qt LGPL en dossier + FFmpeg LGPL, puis faire valider (ceci n'est pas un avis juridique).

## Contradictions et précisions à valider

1. `PROJECT_STATUS.md` demandait de créer le dépôt ; il existe d'après l'utilisateur (contenu et visibilité non lisibles depuis l'environnement de développement : robots.txt).
2. SPEC §9 et critère 12 interdisent « tout service cloud », or Ollama peut en servir via son API locale : garde-fous ajoutés ; **ligne de SPEC à ajouter si vous validez** : « Les modèles Ollama cloud sont interdits au même titre que tout fournisseur distant. »
3. `.gitignore` recommandé : motifs non ancrés dangereux (voir tableau).
4. SPEC cite Gemma 4 12B : il existe, mais son empreinte (de l'ordre de 8 Go quantifié d'après une source secondaire) dépasse probablement la VRAM d'un GPU portable de classe RTX 2050 (≈ 4 Go, à confirmer par `/api/ps`) : E2B/E4B sont les candidats réalistes ; décision après mesures.

## Points à vérifier pendant l’implémentation

- Première source de téléchargement compatible et autorisée pour un test d’intégration.
- Empaquetage Windows et licences des dépendances. *(licences recensées ci-dessus ; empaquetage : phase 7)*
- Modèle local et modalités réellement prises en charge par la version d’Ollama retenue. *(sonde `ollama_probe.py` livrée ; mesures sur le PC cible en attente)*
- Source secondaire de métadonnées/chronologie capable de compléter AniList.
- Qualité des ressources de marque à différentes tailles ; le logo PNG fourni reste la référence approuvée.

Ces points sont des choix à décider au moment où ils deviennent nécessaires ; ils ne justifient pas de retarder les fonctionnalités indépendantes.
