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

## Points à vérifier pendant l’implémentation

- Première source de téléchargement compatible et autorisée pour un test d’intégration.
- Empaquetage Windows et licences des dépendances.
- Modèle local et modalités réellement prises en charge par la version d’Ollama retenue.
- Source secondaire de métadonnées/chronologie capable de compléter AniList.
- Qualité des ressources de marque à différentes tailles ; le logo PNG fourni reste la référence approuvée.

Ces points sont des choix à décider au moment où ils deviennent nécessaires ; ils ne justifient pas de retarder les fonctionnalités indépendantes.
