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
