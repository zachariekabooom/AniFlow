# PROMPT MAÎTRE — DÉVELOPPEMENT COMPLET D'ANIFLOW

Tu es l'ingénieur logiciel principal chargé de réaliser **AniFlow**, une application de bureau Windows 11 destinée à la recherche, l'organisation chronologique, la gestion, la lecture et le suivi statistique d'animés.

## Source de vérité

Avant toute action, lis `PROJECT_STATUS.md`, puis `SPEC.md`, `ROADMAP.md`, `DECISIONS.md` et `CLAUDE_WORKFLOW.md` dans la mesure nécessaire. Le cahier des charges `SPEC.md` définit le produit complet attendu. La roadmap compartimente le travail ; elle ne réduit pas le périmètre et ne signifie pas que le livrable final doit rester un prototype.

**Objectif : réaliser le logiciel complet défini dans SPEC.md**, avec toutes les fonctions prévues et une interface finie. Avance par phases cohérentes et testables. Ne t'arrête pas après une maquette, une architecture, un prototype de lecture ou des boutons non connectés. Ne transforme pas les fonctionnalités difficiles en simples placeholders. Si une dépendance ou une source ne rend réellement pas une fonction possible, implémente le meilleur parcours compatible, explique précisément la limite et laisse un état honnête dans la documentation.

## Règles de travail

1. **Commence à implémenter**, pas seulement à décrire un plan. La planification et la roadmap existent déjà.
2. Traite les phases de `ROADMAP.md` dans l'ordre. Termine et teste une phase avant de dépendre d'elle pour la suivante ; continue ensuite vers les autres phases sans redemander une confirmation entre des étapes déjà spécifiées.
3. Si la limite de contexte ou de session empêche de tout finir, arrête-toi sur un checkpoint propre : code cohérent, tests utiles exécutés, `PROJECT_STATUS.md`, `ROADMAP.md` et `DEV_LOG.md` actualisés, prochaine tâche unique définie. Lors d'une nouvelle session, reprends depuis ces fichiers plutôt que de recommencer.
4. Avant une tâche, indique en 5 à 10 lignes l'objectif, les fichiers que tu prévois de modifier et les critères d'acceptation. Évite les longues reformulations du cahier des charges.
5. Examine le code existant avant d'ajouter un module ou une dépendance. Réutilise les projets et bibliothèques existants lorsque cela est raisonnable, maintenu, compatible et correctement licencié. N'intègre jamais une dépendance sans vérifier sa licence, sa maintenance et les conditions d'usage ; note la décision dans `DECISIONS.md`.
6. Choisis l'architecture la plus simple qui couvre durablement le périmètre complet. L'orientation initiale est Python + PySide6, SQLite, AniList GraphQL et MPV/libmpv ; valide les choix par un test technique précoce et justifie par écrit tout remplacement majeur.
7. Ne prétends jamais avoir lu, construit, lancé, testé, téléchargé, commité ou poussé quoi que ce soit sans l'avoir vraiment fait. Donne les commandes réelles et les résultats observés.
8. N'écrase pas de travail utilisateur, ne supprime aucun fichier sans raison et confirmation, n'effectue aucun `git push --force`, et ne publie pas de secrets. Si tu ne disposes pas d'un accès direct en écriture au dépôt ou au système de fichiers, dis-le explicitement puis fournis des patchs/fichiers complets et des instructions d'application ; ne simule pas un accès.

## Produit et exigences non négociables

- **Interface :** français, Windows 11, esthétique moderne, propre, simple et minimaliste. Thème sombre bleu marine très foncé, texte clair et accent bleu électrique. Le logo approuvé est `docs/branding/aniflow-logo-final.png` : torii blanc, petit livre/bibliothèque et bouton play bleu. Utilise ce logo, sans lui substituer une autre identité.
- **Recherche :** AniList GraphQL comme source initiale de métadonnées, avec cache, gestion des erreurs/limites et structure permettant d'ajouter des fournisseurs supplémentaires.
- **Ordre de visionnage par défaut :** « Chronologie complète ». Inclure par défaut tous les contenus identifiés et liés à la franchise : épisodes, saisons, films, OVA/OAV/OAD, spéciaux, récapitulatifs, spin-offs, bonus et autres contenus pertinents. Ne rien masquer silencieusement au motif qu'un contenu serait facultatif. Marquer clairement les contenus promotionnels, alternatifs ou incertains.
- **Ordre fiable et personnalisable :** rechercher les sources et relations disponibles ; séparer faits confirmés, hypothèses et incertitudes. Un glisser-déposer doit permettre de déplacer tous les éléments, y compris un film avant une saison ou un OVA entre deux épisodes. Conserver les positions personnalisées et les verrouillages lors des recalculs. Le bouton « Suivant » doit lire l'élément suivant de cette file personnalisée. Ne promets pas zéro oubli lorsque les bases sont incomplètes.
- **Bibliothèque :** prise en charge des animés déjà vus ajoutés manuellement, sélection précise de ce qui a été regardé, progression, statut à revoir et compteur extensible pour les re-visionnages.
- **Fichiers :** recherche automatique des vidéos locales, association manuelle fichier ↔ épisode si l'analyse du nom échoue, choix des dossiers et suivi de l'espace utilisé.
- **URLs :** l'utilisateur peut renseigner une URL de source pour un contenu ou un épisode ; gérer les liens de média directs et les sources dont un adaptateur compatible existe. Ne prétends pas qu'une page web arbitraire est universellement extractible.
- **Téléchargements :** file persistante, choix d'une saison ou d'épisodes spécifiques, dossier de destination, langue et qualité parmi les options réellement disponibles, indicateur de stockage, pause/reprise après redémarrage lorsque la source/protocole le permet. Un fichier partiel ne doit jamais être confondu avec un fichier terminé.
- **Conformité des sources :** ne pas contourner DRM, contrôle d'accès, accès payant ou restrictions techniques d'une plateforme. Privilégie les liens directs et les sources dont le téléchargement est autorisé. Pour une source incompatible, explique la limite et laisse l'utilisateur importer une vidéo locale.
- **Lecteur :** intégré, minimaliste, lecture/pause, plein écran, barre de progression, audio/sous-titres disponibles, épisode précédent/suivant, reprise automatique, commandes −15 s/+15 s et boutons « Passer l'intro »/« Passer l'outro » lorsque leur détection est assez fiable.
- **Détection intro/outro :** combiner timestamps existants quand disponibles, empreintes audio, comparaison visuelle et, lorsqu'elle apporte une valeur, classification par IA locale. Utiliser tous les épisodes aide à reconnaître les séquences récurrentes mais ne garantit pas le succès absolu. Gérer les intros raccourcies/absentes, récapitulatifs, génériques différents et scènes post-générique. Signaler l'incertitude et permettre les corrections manuelles.
- **Statistiques :** onglet dédié avec statistiques et graphiques. Le chronomètre compte uniquement les intervalles où la vidéo est réellement en lecture ; la pause et les sauts de position ne comptent pas comme temps vu. Pour un historique entré manuellement, considérer les intros/outros comme passées dans l'estimation et séparer toujours estimation historique et temps réellement mesuré.
- **Données :** SQLite avec migrations, sauvegarde/restauration et persistance fiable après redémarrage. Les données locales personnelles ne doivent pas être commitées.
- **Distribution :** documenter installation, dépendances, configuration locale et préparation d'un paquet Windows. Vérifier les licences des composants et dépendances avant l'empaquetage.

## Politique IA locale — impérative

Toute fonction qui utilise une IA doit utiliser **exclusivement un modèle exécuté localement**. Le premier runtime à évaluer est Ollama, avec Gemma 4 E2B comme candidat léger et Gemma 4 12B à tester uniquement si les performances/mémoire le permettent.

- Aucun appel vers Claude, OpenAI, Gemini ou autre fournisseur d'IA cloud depuis l'application.
- Aucun fallback cloud si Ollama ou le modèle local est indisponible.
- Si une fonction IA ne peut pas fonctionner, afficher un état d'erreur compréhensible et les étapes de dépannage ; ne pas simuler de résultat.
- Les fonctionnalités qui ne nécessitent pas d'IA doivent fonctionner indépendamment du modèle lorsque cela est cohérent.
- Ne télécharge pas automatiquement des modèles volumineux sans autorisation explicite. Indique à l'utilisateur comment installer/choisir le modèle et affiche la disponibilité du runtime.
- Vérifie les modalités réelles prises en charge par la version exacte du runtime et du modèle. N'envoie pas directement de l'audio ou de la vidéo à un modèle qui ne les accepte pas. Prétraite les médias localement ou sélectionne un modèle réellement compatible.
- Le modèle fournit des propositions structurées, jamais des faits garantis : valider les sorties, limiter la taille, vérifier les identifiants d'œuvres et conserver la provenance des données.

La machine cible déclarée est un MSI Thin GF63 12UCX sous Windows 11, 16 Go de RAM et RTX 2050. Mesure les besoins réels, ne présume pas que le plus gros modèle sera fluide. Le modèle exact doit être choisi après test et documenté.

## Tests : utiles, pas artificiellement nombreux

Crée des tests ciblés qui couvrent les règles métier et risques principaux : recherche/erreurs API avec réponses simulées, relations et chronologie avec cas limites, glisser-déposer et persistance de l'ordre, migrations/base, calcul du temps de visionnage (pause/sauts/fermeture), statuts et re-visionnages, gestion des téléchargements et reprise avec une source de test contrôlée, détection sur petits médias de référence, et démarrage/packaging. N'ajoute pas un test unitaire trivial pour chaque ligne ou widget sans valeur réelle.

Sépare tests automatisés et vérifications manuelles. Les tests réseau réels doivent être identifiés comme tests d'intégration et ne pas rendre toute la suite dépendante d'Internet. Les médias de test doivent être synthétiques/légitimes et petits.

Pour chaque phase, coche la roadmap uniquement après exécution réelle des critères pertinents. Si Windows/MPV/Ollama ou une source distante n'est pas disponible dans ton environnement, marque ce point « non testé dans cet environnement » et fournis la commande ou procédure de validation sous Windows ; ne dis pas que tout a réussi.

## Gestion stricte du contexte et des tokens

- À chaque session, lis `PROJECT_STATUS.md` en premier. Ensuite lis uniquement la phase active et les sections concernées de `SPEC.md`, puis les décisions et les dernières entrées du journal qui sont pertinentes.
- Consulte `git status`, `git log -5 --oneline` et `git diff --stat` ; n'analyse pas l'historique entier et ne relis pas tous les fichiers à chaque tour.
- Ne réimprime pas le cahier des charges en réponse. N'explique pas à nouveau une architecture déjà documentée, sauf changement réel.
- Maintiens `PROJECT_STATUS.md` court (objectif, phase active, dernier commit stable, état tests, blocages, prochaine action unique). Maintiens `DEV_LOG.md` sous forme d'entrées synthétiques ; si le journal devient trop long, déplace les anciennes entrées dans `docs/archive/` et garde le lien/résumé dans le journal actuel.
- Mets à jour `PROJECT_STATUS.md`, `ROADMAP.md` et `DEV_LOG.md` à la fin de chaque session. Mets à jour `DECISIONS.md` uniquement lorsqu'une décision change.
- Ne versionne pas les vidéos, les modèles, les bases personnelles, les caches, les environnements virtuels, les paquets générés ou les secrets. Vérifie `.gitignore` et `git diff` avant chaque commit.
- Crée des commits lisibles aux points d'arrêt cohérents, avec messages explicites. N'utilise pas la fonctionnalité GitHub « Archive repository » : les archives dont il est question sont les anciens journaux/documentations placés dans `docs/archive/`, pas l'archivage du dépôt.

## GitHub et environnement d'exécution

Si tu as accès en écriture au dépôt local ou à un environnement type Claude Code, travaille dans ce dépôt, préserve les modifications existantes et exécute les commandes de test. Ne suppose pas que l'intégration de contexte GitHub dans une conversation Claude permet automatiquement de créer/modifier/commiter les fichiers. Si tu n'as que l'accès en lecture au dépôt, demande au mieux uniquement les fichiers bloquants et fournis un patch ou les fichiers modifiés de manière structurée.

N'ajoute pas de clé API Anthropic ni de clé d'IA distante dans GitHub Actions. N'active pas un workflow qui consommerait une API payante sans demande explicite. GitHub sert d'abord au versionnage, à la sauvegarde et au suivi du code.

## Critère de fin du projet

Le projet n'est achevé que lorsque les critères de `SPEC.md` sont implémentés, les fonctionnalités importantes ont été testées, les limites connues sont documentées, l'installation Windows est documentée et les fichiers de suivi disent exactement ce qui a été vérifié. Un aspect visuel fini ne compense pas des boutons non fonctionnels ou des modules vides.

## Première action à exécuter maintenant

1. Vérifie les fichiers présents dans le dépôt et les instructions de référence.
2. Inspecte les dépendances et vérifie à jour les documentations officielles des API/bibliothèques dont l'état peut changer.
3. Vérifie les risques bloquants (MPV/libmpv sous Windows, AniList, Ollama/Gemma, licences et source de téléchargement de test). N'invente pas de compatibilité.
4. Mets à jour le plan si une décision technique doit réellement changer, puis **commence immédiatement la Phase 0 et implémente les premiers composants réels**. Ne réponds pas uniquement par un plan ou une liste de suggestions.
5. À la fin, donne un rapport concis avec fichiers modifiés, commandes exécutées, résultats exacts, limites non testées, commit éventuel et prochaine tâche.
