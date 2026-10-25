# Phase 0 — validation sous Windows 11

Objectif : prouver sur **votre PC** (MSI GF63, Windows 11) ce que l'environnement de développement ne peut pas
tester : AniList en réel, libmpv, intégration Qt, Ollama/Gemma. Chaque sonde produit un rapport JSON ; collez-les
dans la conversation avec Claude. Durée : environ 20 minutes hors téléchargements.

## 0. Prérequis (une seule fois)

| Outil | Installation | Remarque |
|---|---|---|
| Python 3.12, 64 bits | python.org (cocher « Add python.exe to PATH ») | version utilisée pour les tests automatisés |
| Git | git-scm.com | |
| 7-Zip | 7-zip.org | pour extraire libmpv (`.7z`) |
| FFmpeg | `winget install Gyan.FFmpeg` ou ffmpeg.org | génère la vidéo de test |
| Ollama pour Windows | ollama.com | seulement pour l'étape 5 |

## 1. Appliquer l'archive et lancer les tests

À la racine de votre copie locale du dépôt `AniFlow` (PowerShell) :

```powershell
Expand-Archive -Path $HOME\Downloads\aniflow-phase0.zip -DestinationPath . -Force
git status                       # relisez : seuls des fichiers nouveaux ou documentés comme modifiés
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[ui,player]"
python -m unittest discover -s tests -t .
```

Attendu : `Ran N tests … OK` (N = 123 avec les correctifs 1), éventuellement avec `skipped=2` : les deux tests
« module absent » de python-mpv et de PySide6 sont ignorés quand ces modules sont installés. **Aucune** trace
`Exception in thread` ni `Exception occurred during processing` ne doit apparaître. Sinon, copiez la sortie complète.

Pour appliquer un correctif ultérieur (archive incrémentale), même commande à la racine du dépôt :
`Expand-Archive -Path $HOME\Downloads\aniflow-phase0-fix1.zip -DestinationPath . -Force`, puis relancer les tests.

> `.gitignore` est remplacé par une version corrigée (voir `DECISIONS.md`). Le dossier `.venv/` reste ignoré.

## 2. AniList (réseau réel)

```powershell
python tools\phase0\anilist_probe.py --query "Sousou no Frieren" --out reports\anilist.json
```

Réussite : toutes les étapes `ok: true` (`search`, `details_with_relations`, `batch_id_in`, `cache_hit`,
`not_found_is_clean_error`). ≈ 5 requêtes (limite documentée : 30/min en mode dégradé).

## 3. libmpv : lecture, pause, ±15 s, reprise

```powershell
# 3a. libmpv-2.dll : archive « mpv-dev-x86_64-<date>-git-<hash>.7z » (version non « v3 », la plus compatible)
#     https://github.com/shinchiro/mpv-winbuild-cmake/releases   (ou https://github.com/zhongfly/mpv-winbuild/releases)
#     Extraire libmpv-2.dll dans third_party\libmpv\   (dossier ignoré par Git)
python tools\phase0\make_test_media.py --out reports\test-60s.mp4
python tools\phase0\mpv_probe.py --file reports\test-60s.mp4 --dll-dir third_party\libmpv --headless --out reports\mpv-headless.json
python tools\phase0\mpv_probe.py --file reports\test-60s.mp4 --dll-dir third_party\libmpv --out reports\mpv-window.json
```

Réussite : les 7 contrôles `ok: true` dans les deux modes (le second ouvre la fenêtre mpv avec le son, ≈ 12 s).

Puis l'intégration dans une fenêtre Qt (contrôle visuel) :

```powershell
python tools\phase0\qt_smoke.py --video reports\test-60s.mp4 --dll-dir third_party\libmpv --out reports\qt.json
```

À vérifier à l'écran : fond bleu marine très foncé ; **logo AniFlow visible** ; mire vidéo dans le cadre ;
« Lecture / Pause », « −15 s » et « +15 s » fonctionnent ; le compteur avance. Fermez la fenêtre : le rapport s'écrit.

## 4. (Optionnel) Même mesure sans fenêtre pour un diagnostic

Si l'étape 3 échoue : `--dll-dir` doit pointer vers le dossier contenant `libmpv-2.dll`, Python et la DLL doivent
être tous deux en 64 bits, et le rapport JSON contient `mpv_log` (messages de libmpv).

## 5. Ollama local et Gemma 4

```powershell
setx OLLAMA_NO_CLOUD 1          # désactive les fonctions cloud d'Ollama (FAQ officielle) ; puis quittez et relancez Ollama
ollama pull gemma4:e2b          # téléchargement volontaire de plusieurs Go : AniFlow ne le fait jamais seul
python tools\phase0\ollama_probe.py --model gemma4:e2b --out reports\ollama-e2b.json
```

Réussite : `état_du_modèle` = `ready`, `génération_structurée` ok, et le rapport indique `modalités` (vision, audio,
thinking), le débit en jetons/s et la mémoire GPU utilisée (`mémoire_en_cours`). Pour comparer, répétez avec
`gemma4:e4b`, puis `gemma4:12b` si l'espace disque le permet : c'est ce qui décidera du modèle par défaut.

## 6. Ce qu'il faut renvoyer

Collez le contenu de `reports\anilist.json`, `mpv-headless.json`, `mpv-window.json`, `qt.json` et
`ollama-*.json`, plus la sortie de l'étape 1, et dites ce que vous avez vu à l'écran (logo, vidéo, boutons).
Les rapports contiennent la version de Windows/Python et des chemins locaux : relisez-les avant de les partager.

> Accents mal affichés dans la console (PowerShell 5, invite de commandes) : c'est l'affichage, pas les données.
> Les scripts écrivent en UTF-8 ; ouvrez les fichiers `reports\*.json` avec VS Code ou `Get-Content -Encoding UTF8`,
> ou lancez `chcp 65001` avant les commandes.
