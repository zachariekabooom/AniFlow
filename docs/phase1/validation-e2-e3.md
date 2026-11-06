# Validation sous Windows — E2 (démarrage) et E3 (fenêtre principale)

À exécuter sur le PC de l'utilisateur, à la racine du dépôt, environnement virtuel activé. Rien n'est coché `[x]` dans
`ROADMAP.md` avant que ces résultats aient été communiqués.

## 1. Tests automatiques

```powershell
python -m unittest discover -s tests -t .
```

Attendu : `OK`. Les tests Qt (`tests/ui/*`, 36) s'exécutent car PySide6 est installé ; `skipped=2` correspond aux deux tests
« module absent » de python-mpv et de PySide6 (jusqu'à 3 si la fenêtre ne peut pas être activée hors écran : le test
« touches Ctrl+chiffre pressées » s'ignore alors). Aucune trace `Exception in thread`. Pour ne lancer que l'interface :

```powershell
python -m unittest tests.ui.test_main_window tests.ui.test_application tests.ui.test_smoke_subprocess -v
```

## 2. Smoke-test

```powershell
python -m aniflow --smoke-test
$LASTEXITCODE
```

Attendu : la fenêtre apparaît brièvement, puis `AniFlow : démarrage OK (smoke-test)` et `0`. Le journal
`%LOCALAPPDATA%\AniFlow\logs\aniflow.log` contient `Smoke-test : démarrage OK` et **aucune** ligne `Could not parse` ni
`Unknown property` (feuille de style acceptée par Qt). Le smoke-test n'enregistre aucune préférence.

## 3. Lancement normal — contrôles visuels

```powershell
python -m aniflow
```

- [ ] La fenêtre s'ouvre (1280 × 800 par défaut) : fond bleu nuit, **barre de titre sombre** (sinon, le noter : c'est le point d'E8).
- [ ] Barre latérale : logo + « AniFlow », puis, dans cet ordre exact : Accueil / Continuer, Recherche, Ma bibliothèque, Téléchargements, Statistiques, Paramètres ; version en bas.
- [ ] Entrée active : fond bleu sombre + liseré clair à gauche ; survol : fond plus clair ; texte lisible partout.
- [ ] `Tab` / `Maj+Tab` : anneau de focus clair visible sur chaque entrée, dans l'ordre ; `Entrée` et `Espace` ouvrent la section.
- [ ] `Ctrl+1` … `Ctrl+6` ouvrent les six sections. **Clavier AZERTY** : essayer `Ctrl+&`, `Ctrl+é`… (touches sans Maj) puis `Ctrl+Maj+chiffre`, et noter ce qui fonctionne.
- [ ] Flèches haut/bas avec le focus dans la barre latérale : noter le comportement (Qt peut déplacer l'entrée active).
- [ ] Chaque page : titre + carte « n'est pas encore disponible » avec la phase prévue ; **aucun bouton, champ ou fonction simulée**.
- [ ] Redimensionner : impossible sous 960 × 600 ; à 1920 × 1080 et 1366 × 768 rien n'est coupé.
- [ ] Choisir « Statistiques », déplacer et redimensionner la fenêtre, fermer, relancer : même section, même position et même taille.
- [ ] (Facultatif) Échelle Windows 125 % puis 150 % : texte et logo nets, rien ne déborde.
- [ ] Après la fermeture, plus de processus `python` actif (Gestionnaire des tâches).

## 4. Erreurs de démarrage (facultatif, sans danger : dossier de données temporaire)

```powershell
$env:ANIFLOW_HOME = "$env:TEMP\AniFlowTest"
New-Item -ItemType Directory -Force $env:ANIFLOW_HOME | Out-Null
@'
import os, sqlite3
c = sqlite3.connect(os.path.join(os.environ["ANIFLOW_HOME"], "aniflow.db"))
c.execute("PRAGMA user_version = 99")
c.commit()
c.close()
'@ | python -
python -m aniflow
$LASTEXITCODE
```

Attendu : une boîte de dialogue lisible (« Base de données plus récente »), **aucune trace Python**, code `2`. Nettoyage :

```powershell
Remove-Item -Recurse -Force $env:ANIFLOW_HOME
Remove-Item Env:ANIFLOW_HOME
```

## 5. À renvoyer

La sortie complète des tests, les résultats des sections 2 à 4 (coches et observations, surtout : barre de titre, logo,
raccourcis AZERTY, focus) et, si possible, une capture d'écran de la fenêtre (à ne pas committer : elle peut montrer des
chemins personnels).
