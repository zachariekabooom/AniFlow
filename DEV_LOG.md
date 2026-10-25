# DEV_LOG — AniFlow

Journal concis : une entrée par session, résultats réellement observés. Les anciennes entrées iront dans `docs/archive/`.

## 2026-10-24 — Phase 0 (code et sondes) + socle non graphique de la phase 1

**Contexte :** environnement sans réseau sortant, sans Windows, sans PySide6, libmpv, Ollama ni pytest ; Python 3.12.3, SQLite 3.45.1, FFmpeg 6.1.1 présent. Dépôt GitHub non lisible (robots.txt) et sans accès en écriture.

**Livré :** `src/aniflow/{net,services/anilist,services/ai,services/player,database,ui/theme}`, `paths.py`, `logging_setup.py`, `tools/phase0/*`, `docs/phase0/validation-windows.md`, `tests/`, `pyproject.toml`, `.gitignore` corrigé ; `DECISIONS.md`, `ROADMAP.md`, `PROJECT_STATUS.md`, `README.md` mis à jour.

**Vérifié par recherche (sources dans `DECISIONS.md`) :** limite AniList dégradée à 30/min et CGU ; types de relation dont SUMMARY ; modèles Ollama « cloud » appelables par l'API locale ; Gemma 4 (tailles, audio ≤ 30 s, E2B/E4B/12B) ; python-mpv et builds libmpv Windows (licences) ; format de l'API AniSkip.

**Commandes et résultats :**
- `python3 -m unittest discover -s tests -t .` → `Ran 113 tests … OK` (deux exécutions, dont `python3 -X dev -W default` : aucun avertissement de ressource).
- `python3 tools/phase0/make_test_media.py` (dans un test) → vidéo synthétique avec audio et vidéo, durée conforme, < 300 Ko.
- Test du `.gitignore` recommandé avec `git -c core.ignorecase=true check-ignore` : ignorait `src/aniflow/services/downloads/`, `…/ai/models/` et `…/ui/media/` → remplacé par une version ancrée, 14 cas vérifiés.
- Relecture « Windows » (corrigée avant livraison) : `os.add_dll_directory` lève si le dossier est absent (garde ajoutée, test), sorties des sondes forcées en UTF-8 (console cp1252), restauration d'une sauvegarde absente = message français (test).
- Contrastes de la palette mesurés : texte/fond 16,0:1 ; texte secondaire/fond 7,8:1 ; blanc sur bouton principal 5,0:1 (survol 4,7:1) ; accent/fond 3,8:1 (élément non textuel).

**Non testé (aucun moyen ici) :** AniList réel (schéma validé sur la documentation, pas sur l'API), libmpv, Windows, PySide6 et logo, Ollama/Gemma réels, installation depuis `pip install -e .[ui,player]`.

**Prochaine tâche :** exécuter `docs/phase0/validation-windows.md` sur le PC cible et fournir les rapports JSON.

## 2026-10-24 (2) — Retour d'exécution Windows 11 / Python 3.12.10 : correctifs 1

**Retour de l'utilisateur (non reproductible ici) :** `python -m unittest discover -s tests -t .` avec `.[ui,player]` → 113 tests, 1 échec, 2 ignorés (cohérent avec les deux tests « module absent » de python-mpv et PySide6), plus une `UnicodeDecodeError` (octet 0xe9) dans un thread de lecture de sous-processus et une `ConnectionAbortedError` (WinError 10053) dans `tests/support/servers.py` ligne 62.

**Causes établies — reproduites par simulation sous Linux (Python 3.12.3) ; aucune exécution sous Windows par l'assistant :**
1. *Échec local-only.* `_is_loopback_host` déléguait à `ipaddress.ip_address(host).is_loopback`, dont la sémantique pour les adresses IPv4-mappées varie selon les correctifs de CPython (3.12.3 : `::ffff:127.0.0.1` → False ; 3.12.10, cohérent avec l'échec observé : accepté). Mécanisme reproduit en simulant la sémantique récente. L'analyse a aussi montré que l'ancien code acceptait, même en 3.12.3, `[::1%25lo]` (zone), `127.0.0.1.` et `localhost.` (point final), et laissait fuiter un `ValueError` brut pour `[127.0.0.1]`.
2. *UnicodeDecodeError.* `tools/phase0/make_test_media.py` était le seul script à ne pas importer `_common` (UTF-8 forcé) et il affiche « Vidéo de test créée » : la sortie d'un tube Windows est en cp1252 (é = 0xE9) alors que le test décodait en UTF-8 avec `text=True`. L'erreur survenait dans le thread de lecture de `communicate()` et ne faisait pas échouer le test. Reproduit avec `PYTHONIOENCODING=cp1252` : `'utf-8' codec can't decode byte 0xe9 in position 3`. Les quatre autres sondes émettaient déjà de l'UTF-8 valide.
3. *WinError 10053.* `Handler._handle` n'attrapait que `BrokenPipeError` et `ConnectionResetError` ; un client qui a coupé produit `ConnectionAbortedError` sous Windows. Tests qui coupent volontairement le client : `test_slow_server_times_out` (délai serveur 1,0 s, timeout client 0,2 s) et `test_oversized_response_is_refused`. Reproduit en simulant l'exception : l'ancien serveur imprimait la trace via `socketserver` sans faire échouer le test.

**Corrections :**
- `src/aniflow/net/local_only.py` : liste blanche explicite + forme canonique (plus de `is_loopback`), `ValueError` d'analyse converties en `NotLocalError`, crochets réservés à l'IPv6, plus de suppression du point final.
- `tools/phase0/_common.py` (`force_utf8_output`, stdout strict, stderr `backslashreplace`) ; `make_test_media.py` importe `_common`, message accentué, sortie de FFmpeg décodée explicitement.
- `tests/support/servers.py` : déconnexion tolérée seulement si déclarée et comptée, autres exceptions → échec du test, attente des réponses en cours.
- Tests : `test_ollama_client.py` (+3, le cas `::ffff:127.0.0.1` d'origine est conservé tel quel), `test_probe_scripts.py` (octets, décodage strict, console cp1252 simulée, +2), `test_support_servers.py` (+5), `test_anilist_client.py` (2 tests déclarent l'abandon du client).

**Résultats (Linux, Python 3.12.3) :**
- Avant correction : `python3 -m unittest tests.test_ollama_client tests.test_probe_scripts tests.test_support_servers` → `Ran 41 tests … FAILED (failures=10, errors=1)`.
- Après : `python3 -m unittest discover -s tests -t .` → `Ran 123 tests … OK`, trois exécutions consécutives ; `python3 -X dev -W default …` → `OK`, 0 trace ou avertissement.
- `PYTHONIOENCODING=cp1252 PYTHONUTF8=0 python3 tools/phase0/make_test_media.py` → sortie décodée en UTF-8 strict : « Vidéo de test créée … ».

**Non testé :** toute exécution sous Windows (3.12.10 compris) : sémantique `ipaddress` récente, console cp1252 et WinError 10053 sont simulées. La phase 0 n'est pas terminée.

**Prochaine tâche :** appliquer `aniflow-phase0-fix1.zip`, relancer la suite sous Windows et renvoyer la sortie complète.

## 2026-10-25 — Validation de la phase 0 sous Windows 11 (preuves réelles)

**Sources :** six rapports JSON produits par les sondes sur le PC de l'utilisateur (Windows 11 10.0.22631, Python 3.12.10, AMD64) et le message de l'utilisateur. Aucun test supplémentaire n'a été exécuté de mon côté : les rapports ont été relus et recoupés (champs `ok`, arithmétique des limites, cohérence entre rapports). Horodatages en UTC.

**Suite automatisée** (communiqué par l'utilisateur ; sortie complète non jointe) : 123 tests exécutés, OK, 2 ignorés.

**AniList réel** (`anilist.json`, 02:10) : 5 étapes sur 5 `ok`.
- Recherche « Sousou no Frieren » : 0,284 s, 5 résultats (154587 TV 28 ép. 2023 ; 209939 « 3rd Season » TV, ép. inconnus, 2027 ; 182255 « 2nd Season » TV 10 ép. 2026 ; 170068 et 189513 « ●● no Mahou », ONA 12 et 6 ép.). `pageInfo.total` = 5000 : valeur ronde, probablement plafonnée.
- Fiche du premier résultat : 0,501 s, `idMal` 52991, 6 relations (SOURCE 1, CHARACTER 1, SIDE_STORY 2, OTHER 1, SEQUEL 1), 0 illisible : `relationType(version: 2)` accepté.
- Lot `id_in` : 6 demandées (la fiche + 5 relations animées, la source manga exclue), 6 reçues, 0 absente, 0,534 s.
- Cache : second appel en 0,09 ms. Fiche inexistante : erreur propre (« HTTP 404 : Not Found. »).
- En-tête `X-RateLimit-Limit` = 30 ; `remaining` 29, 28, 27, 27, 25 après 5 requêtes réseau (cohérent) : le mode dégradé à 30/min est confirmé en direct.
- Non exercés en réel : réponse 429, recherche avec `include_adult=True`.

**libmpv** (`mpv-headless.json` 02:16, `mpv-window.json` 02:20) : 7 contrôles sur 7 `ok` dans chaque mode ; build `mpv v0.41.0-1227-ge471496c5`, FFmpeg `N-127893-g9a861e968` ; `mpv_log` vide.
- Headless : démarrage 0,047 s ; lecture 3,00 s mesurés pour 3,0 attendus ; pause sans dérive ; ±15 s exacts (3,08 → 18,08 → 3,08) ; seek absolu 30,0 ; reprise à 30,0.
- Fenêtre : démarrage 0,218 s ; lecture 2,68 s mesurés pour 3,0 attendus (écart de 0,32 s dans la tolérance de 1,5 s, non investigué) ; autres mesures identiques. Image et son constatés par l'utilisateur.

**Qt** (`qt.json`, 12:35) : `logo_loaded` = true, `ok` = true. Échantillons de position : 0,0 → 1,92 → 3,96 → 30,24 → 10,84 → 30,04 → 31,08 (×4) : progression régulière, sauts dans les deux sens, plateau final — compatibles avec ±15 s et pause. Le critère automatique du script (dernier échantillon > premier) est faible : la preuve repose sur le contrôle visuel de l'utilisateur (Lecture/Pause, −15 s, +15 s). Le rendu du thème (fond bleu marine, lisibilité) n'a pas été confirmé explicitement.

**Ollama + Gemma 4** (`ollama-e2b.json` 12:42, `ollama-e4b.json` 12:49) : Ollama 0.40.8 ; `OLLAMA_NO_CLOUD=1` déclaré par l'utilisateur (non vérifiable par les rapports) ; les deux sondes `ok`.
- `gemma4:e2b` : 4,59 Go sur disque, 4.6B, Q4_K_M ; `gemma4:e4b` : 6,58 Go, 7.5B, Q4_K_M ; aucune entrée distante.
- Capacités annoncées identiques : audio, completion, thinking, tools, vision ; contexte max 131072 ; sortie JSON structurée conforme (`{"answer": "ok"}`) pour les deux.
- Mesures brutes du test de 7 jetons générés (**non interprétables**) : E2B chargement 56,70 s, durée murale 80,77 s, 60,1 jetons/s ; E4B chargement 21,61 s, durée murale 36,93 s, 17,6 jetons/s.
- `/api/ps` : 0,32 Go (E2B) et 0,34 Go (E4B), tout en VRAM.

**Ce qui n'est PAS conclu :**
- Qualité ou performances des modèles : un test de 7 jetons ne mesure ni l'une ni l'autre ; E2B (testé en premier : démarrage à froid, cache disque) et E4B ne sont pas comparables. E2B et E4B restent candidats ; Gemma 4 12B n'a pas été testé.
- Mémoire : 0,32 et 0,34 Go sont incompatibles avec des modèles de 4,59 et 6,58 Go (7,0 % et 5,2 % de la taille sur disque) : valeurs ininterprétables, à mesurer avec `nvidia-smi` / Gestionnaire des tâches.
- 24,1 s (E2B) et 15,3 s (E4B) de durée murale ne sont expliquées ni par le chargement ni par la génération ; `total_duration` n'est pas journalisé par la sonde.
- Audio : capacité annoncée, mode d'envoi via l'API non vérifié (le client refuse l'audio).

**Licences vérifiées ce jour (sources dans `DECISIONS.md`) :** Gemma 4 : Apache 2.0 (annonce officielle de Google) ; PySide6 : édition communautaire LGPLv3/GPLv3 ou édition commerciale.

**Verdict :** les critères techniques de faisabilité de la phase 0 sont satisfaits sur preuves réelles (6 critères sur 8 cochés). La phase n'est pas cochée : deux vérifications non techniques restent — (1) dépôt privé, kit et code de la phase 0 committés et poussés ; (2) décision de distribution. Aucun test à refaire.

**Prochaine tâche :** obtenir ces deux confirmations de l'utilisateur ; la phase 0 est alors cochée.

