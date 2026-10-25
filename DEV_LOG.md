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
