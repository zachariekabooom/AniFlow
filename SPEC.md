# AniFlow — cahier des charges fonctionnel et technique

**Version :** 0.4 — spécification validée pour le lancement du développement  
**Plateforme cible :** Windows 11  
**Langue de l'interface :** français  
**Type :** application de bureau de gestion, d'organisation et de lecture d'animés  
**État :** spécification en cours de planification ; le projet n'est pas encore développé.

## 1. Vision et principes

AniFlow est une bibliothèque personnelle d'animés qui transforme une franchise en parcours de visionnage suivi de bout en bout. L'utilisateur recherche une série, obtient un ordre de visionnage aussi complet et chronologique que les données disponibles le permettent, regroupe les saisons, épisodes, OVA/OAV, films et spéciaux dans une file unique, puis utilise « Suivant » pour passer automatiquement au prochain élément recommandé.

L'application doit privilégier les solutions gratuites, locales, modulaires et simples à maintenir. Toute fonctionnalité qui utilise une IA doit utiliser exclusivement une IA exécutée localement ; aucun service cloud ni solution distante de repli ne doit être utilisé. Si le moteur local est indisponible, la fonction IA doit afficher une erreur claire et ne pas basculer vers un fournisseur distant. Les fonctionnalités ne nécessitant pas d'IA restent utilisables selon leurs propres dépendances. Les incertitudes de métadonnées doivent rester visibles : le logiciel ne doit jamais présenter comme certain un ordre qu'il ne peut pas vérifier.

## 2. Recherche et fiches

- Barre de recherche avec résultats pendant la saisie et prise en charge des titres romaji, japonais, anglais et alternatifs disponibles.
- AniList GraphQL est la source de départ pour les métadonnées, affiches, titres, formats, genres, dates, durées et relations entre œuvres.
- Une couche d'abstraction doit permettre d'ajouter d'autres sources à l'avenir sans réécrire l'interface.
- Afficher une fiche d'œuvre avec son synopsis, ses genres/tags, son année, son format, son nombre d'épisodes connu et les œuvres liées.
- Mettre les réponses en cache local, limiter les requêtes, traiter les erreurs réseau et les limites de débit de l'API.
- Une donnée indisponible doit être affichée comme inconnue, et non inventée.

## 3. Ordre de visionnage — fonction centrale

### 3.1. Mode par défaut : « Chronologie complète »

Le mode par défaut est **Chronologie complète**. Il doit inclure par défaut tous les contenus connus et reliés à la franchise, y compris les récapitulatifs, bonus, OVA/OAV, OAD, films, épisodes spéciaux, histoires parallèles, spin-offs et autres dérivés identifiés. Aucun contenu découvert ne doit être exclu silencieusement parce qu'il est jugé facultatif. Les contenus alternatifs, récapitulatifs et promotionnels doivent être étiquetés clairement, mais rester visibles dans le parcours par défaut.

Le but est de placer chaque contenu dans l'ordre interne de l'histoire lorsqu'il est connu, sans utiliser les dates de sortie comme règle principale. Lorsque le placement exact ne peut pas être établi, conserver l'élément dans la liste et signaler qu'il est à trier. La file représente des éléments de lecture : un épisode individuel lorsqu'il faut insérer un contenu au milieu d'une saison, ou un film/OVA/spécial comme une unité de lecture.

L'objectif UX est que l'utilisateur clique sur **Suivant** et que l'application enchaîne sur le bon élément, même lorsqu'il faut passer de la fin d'une saison à quelques épisodes spéciaux ou à un film avant la saison suivante.

### 3.2. Modes complémentaires

- **Chronologie complète** (par défaut) : tous les contenus connus de la franchise, récapitulatifs compris, triés dans la chronologie interne la mieux établie.
- **Histoire principale** : vue filtrée du parcours pour ne montrer que les éléments nécessaires à l'intrigue centrale, sans supprimer les autres contenus de la base.
- **Ordre de sortie** : alternative basée sur les dates connues.
- **Liste intégrale** : tous les éléments découverts, y compris les œuvres alternatives ou promotionnelles, sans prétendre que leur ordre chronologique est certain.

### 3.3. Logique de construction

- Explorer récursivement les relations entre œuvres fournies par AniList.
- Chercher, si besoin, une corroboration dans des sources additionnelles identifiées dans l'architecture, avec leur attribution.
- Employer des règles déterministes pour les cas connus et une IA locale comme assistante pour classer/expliciter des propositions, jamais comme unique source de vérité.
- Pour chaque élément, enregistrer le type, le rang, la source, le motif du placement et un niveau de confiance : vérifié, probable ou à confirmer.
- Distinguer préquelle, suite, histoire parallèle, spin-off, récapitulatif, univers alternatif et contenu promotionnel quand les sources le permettent.
- Ne jamais supprimer silencieusement un contenu découvert parce que son emplacement est incertain. Le conserver dans le parcours et le signaler « À trier / emplacement incertain ».
- Prévoir un système de **glisser-déposer** pour réordonner les saisons, épisodes individuels, films, OVA, récapitulatifs et spéciaux dans une seule liste. Exemple : déplacer un film avant la saison 2 ou insérer un OVA entre deux épisodes.
- Permettre de verrouiller la position d'un élément, de le marquer comme vérifié, ou de le masquer uniquement sur demande explicite. Conserver les corrections locales et ne jamais les écraser au recalcul.
- Le bouton « Suivant » lit l'élément suivant de cette liste personnalisée, quel que soit son type.
- Si plusieurs ordres sont plausibles, afficher l'incertitude et expliquer brièvement le conflit.

### 3.4. Limite à reconnaître

Aucune base généraliste ne garantit à elle seule une chronologie complète et incontestable épisode par épisode pour chaque franchise. La complétude dépend des données disponibles et de règles entretenues. Un parcours peut être très fiable, mais AniFlow ne doit pas promettre « aucun oubli garanti » lorsque des OVA rares, films régionaux ou épisodes spéciaux manquent des bases consultées.

## 4. Bibliothèque, suivi et visionnages répétés

- Galerie de titres avec affiche, nom, progression, dernier élément lu et dernière date de lecture.
- Statuts : À regarder, En cours, En pause, Terminé, Abandonné, **À revoir**, **Revu 1 fois**, **Revu 2 fois**. L'implémentation devra également conserver un compteur de visionnages pour permettre « Revu 3 fois » et plus sans figer la liste de statuts.
- Pouvoir ajouter manuellement des animés déjà vus. Proposer une action « Marquer toute la chronologie comme déjà vue » ou une sélection granulaire des saisons, films, OVA et spéciaux effectivement regardés.
- L'ajout historique doit compter tous les éléments sélectionnés de la franchise dans les statistiques de titres/épisodes terminés, y compris films et OVA. Ne pas inventer une durée de chronomètre réelle : afficher séparément la durée historique estimée et le temps réellement mesuré par le lecteur.
- Les titres ajoutés manuellement comme déjà vus sont considérés comme ayant eu leurs intros et outros passées pour l'estimation historique, en utilisant les durées connues de ces séquences. Si elles sont inconnues, la durée estimée doit être signalée comme approximative.
- Recherche, filtres et tris par titre, genre, statut, progression et date d'activité.
- Permettre la correction des métadonnées, de l'historique et des compteurs de visionnage.

## 5. Fichiers locaux et stockage

- Ajouter un ou plusieurs dossiers locaux et détecter les fichiers vidéo pris en charge.
- Associer les fichiers à la bonne œuvre et au bon épisode à partir du nom du fichier ; toute association incertaine doit pouvoir être corrigée manuellement.
- Permettre d'ajouter manuellement un fichier vidéo précis à une œuvre ou à un épisode via un sélecteur de fichiers, y compris lorsque la détection automatique ne trouve rien.
- Permettre d'enregistrer une URL de source pour une œuvre ou un épisode manquant ; si l'URL fournit directement un fichier téléchargeable ou est gérée par un adaptateur de source compatible, l'ajouter au gestionnaire de téléchargements. Une page web générique ne garantit pas que son média soit extractible.
- Afficher l'espace occupé par AniFlow, la taille des fichiers téléchargés et l'espace libre sur le disque de destination.
- Permettre de choisir ou changer le dossier de téléchargement. Le changement doit préciser s'il s'applique uniquement aux nouveaux fichiers ou aussi aux fichiers existants.
- Afficher séparément les médias disponibles localement, manquants et en cours de téléchargement.
- Ne jamais déplacer, renommer ou effacer de fichier sans action explicite de l'utilisateur.

## 6. Téléchargements — gestionnaire modulaire

### 6.1. Parcours utilisateur

L'utilisateur configure une source ou fournit l'URL d'une page de recherche prise en charge. AniFlow cherche le titre, affiche les résultats possibles pour que l'utilisateur confirme le bon animé, puis parcourt les saisons et épisodes disponibles. L'utilisateur peut commencer à n'importe quelle saison (par exemple saison 2), sélectionner certains épisodes ou toute une saison, et choisir la qualité et la langue lorsqu'elles sont réellement proposées par la source.

Chaque élément de la chronologie doit aussi permettre de renseigner manuellement une URL de source. Le gestionnaire essaie de la traiter par téléchargement direct ou via un adaptateur déclaré compatible ; si elle pointe uniquement vers une page non prise en charge, il doit expliquer cette limite au lieu de prétendre pouvoir en extraire la vidéo.

Langues à prendre en charge lorsqu'elles existent : VF, VOSTFR et VOSTA. La qualité doit être choisie parmi les formats réellement disponibles sur la source ; ne pas inventer une option absente.

### 6.2. Fonctions du gestionnaire

- File persistante de téléchargements : en attente, en cours, en pause, terminé, échec.
- Pause/reprise, y compris après fermeture ou redémarrage du PC, lorsque le protocole ou l'extracteur source prend en charge la reprise.
- Mémoriser l'épisode, la source, les options choisies, le chemin temporaire et l'état de la tâche.
- Conserver les téléchargements incomplets sans les confondre avec des fichiers terminés.
- Afficher progression, débit, taille reçue, taille totale quand connue, espace libre, erreurs et action « réessayer ».
- Ne pas relancer un épisode déjà téléchargé sans demander confirmation ou vérifier qu'il est incomplet.
- Après succès, associer le fichier à l'œuvre et à l'épisode concernés.

### 6.3. Faisabilité et compatibilité des sources

Il est impossible de garantir le fonctionnement avec une URL arbitraire de n'importe quel site sans adaptateur approprié. Il faut concevoir une interface d'adaptateur par source : un extracteur réutilisable peut suffire pour les sources compatibles ; d'autres nécessiteront un adaptateur dédié et des tests de maintenance. L'automatisation de pages Web ne doit être qu'un mécanisme de dernier recours pour les sources compatibles.

Le périmètre couvre les médias que l'utilisateur a le droit de télécharger et les sources qui exposent un téléchargement compatible. Il ne faut pas implémenter de contournement de DRM, d'accès payant ou de contrôles d'accès. Si une source n'est pas compatible, AniFlow doit expliquer la limitation et laisser importer les fichiers localement ou utiliser la source officielle.

## 7. Lecteur vidéo

Lecteur intégré minimaliste, avec affichage des commandes au survol ou à la demande :

- lecture/pause, barre de progression et volume ;
- raccourcis **−15 s** et **+15 s** ;
- plein écran et navigation clavier ;
- épisode précédent/suivant ;
- nom de l'œuvre, de la saison et de l'épisode ;
- pistes audio et sous-titres quand le moteur/format les expose ;
- reprise à la dernière position ;
- bouton « Passer l'intro » / « Passer l'outro » quand une plage est connue avec une confiance suffisante ;
- bouton pour désactiver ou corriger la détection.

Le lecteur doit être testé tôt avec un prototype avant de choisir définitivement l'intégration. MPV/libmpv constitue la première option à évaluer.

## 8. Détection des intros, outros et génériques

### 8.1. Approche en plusieurs niveaux

1. Consulter une base de timestamps communautaire comme AniSkip lorsqu'une entrée correspond à l'identifiant de l'œuvre et au numéro d'épisode. Mettre les réponses en cache.
2. Si aucune plage fiable n'existe, comparer l'audio des épisodes d'une même série pour retrouver des séquences musicales récurrentes, puis vérifier la correspondance avec des empreintes audio.
3. Utiliser des signaux visuels en complément : similarité d'images, séquences récurrentes, transitions et génériques crédités.
4. Une IA locale multimodale peut classifier des échantillons (intro, épisode principal, crédits, récapitulatif) et aider à suggérer des bornes. Les timestamps définitifs doivent être validés par des indices audio/visuels et des contrôles de cohérence.
5. Permettre l'extraction d'un échantillon de référence et la correction manuelle par l'utilisateur.

### 8.2. Limites à prendre en compte

Le fait de disposer de tous les épisodes aide à comparer les séquences, mais ne rend pas la détection infaillible. Certaines intros ont une version raccourcie, sont supprimées dans un épisode, commencent à des positions différentes, ou sont précédées d'un résumé ; des scènes post-générique peuvent aussi être prises pour l'outro. L'application doit proposer la plage avec une confiance, la mettre en cache par fichier/version et éviter les sauts automatiques incertains.

Les modèles de langage ne doivent pas analyser seuls chaque seconde de chaque vidéo : c'est plus lent et moins précis qu'une analyse ciblée par audio/vidéo. Utiliser une méthode hybride, économique et locale par défaut.

## 9. IA locale — obligatoire pour tout usage de l'IA

- Lorsqu'une fonctionnalité utilise de l'IA, elle doit passer exclusivement par un modèle exécuté localement. Aucun fournisseur cloud, API IA distante ni repli distant n'est autorisé.
- Prévoir un unique point d'intégration pour Ollama local dans un premier temps, avec sélection/configuration du modèle local et vérification de disponibilité.
- Gemma 4 E2B peut être évalué pour les tâches légères ; Gemma 4 12B pour les tâches plus complexes si les ressources et le runtime le permettent. Ne pas supposer que toutes les modalités (audio, vidéo, image) sont exposées par la même version d'Ollama : vérifier les capacités réelles du runtime et du modèle avant de concevoir un workflow multimodal.
- Les tâches concernées peuvent inclure l'aide au classement des relations, le rapprochement de titres, la classification de segments, la formulation d'explications et l'aide au tri des cas ambigus.
- Les résultats doivent être structurés, validés et comparés aux sources ; la réponse de l'IA n'est jamais une donnée officielle par défaut.
- Si Ollama ou le modèle local est absent/inaccessible, une fonctionnalité IA doit afficher une erreur exploitable, proposer les étapes de dépannage et ne jamais basculer vers un service distant. Les fonctionnalités non-IA restent accessibles si elles sont indépendantes du service.
- Ne pas télécharger de modèle volumineux sans autorisation explicite. Afficher le modèle actif, sa taille lorsque connue, la disponibilité, l'utilisation éventuelle et la configuration retenue.
- Respecter la confidentialité : les échantillons audio/vidéo peuvent être analysés localement, sans envoi automatique à un serveur externe.

## 10. Statistiques — onglet dédié

L'onglet Statistiques doit regrouper les indicateurs et graphiques suivants :

- temps réellement regardé mesuré par le lecteur ;
- estimation séparée du temps d'historique avant AniFlow ;
- temps par jour, semaine, mois, année et série ;
- épisodes, films, OVA et épisodes spéciaux terminés ;
- animés commencés, terminés, en cours et à revoir ;
- répartition des titres et du temps par genres/tags ;
- progression de la bibliothèque dans le temps ;
- historique des sessions et longues périodes d'activité ;
- nombre de re-visionnages ;
- médias les plus vus et moyenne de durée de session.

Le chronomètre fonctionne tant que le lecteur indique que la vidéo est en lecture. Il s'arrête pendant la pause, à la fermeture du lecteur, à l'arrêt du média et quand la lecture échoue. Les sauts vers l'avant ne doivent pas compter comme du temps regardé : le temps mesuré vient de l'horloge monotone pendant les périodes réellement en lecture, et la progression média est suivie séparément.

Les proportions doivent afficher leur dénominateur. Exemple : « 70 % des titres comportent le genre action » ne signifie pas que 70 % du temps regardé correspond à l'action. Permettre de distinguer les deux calculs.

## 11. Design et ergonomie

- Interface moderne, propre et minimaliste, pensée comme une application média premium, pas comme un outil technique.
- Thème sombre obligatoire, basé sur un bleu marine très foncé (fond principal proche de #080D1A / #0B1020), avec surfaces légèrement plus claires, texte blanc cassé/gris et bleu électrique en accent. Les valeurs exactes peuvent être ajustées après maquette.
- Hiérarchie visuelle nette, marges généreuses, cartes d'animés soignées, affiches lisibles, coins légèrement arrondis et transitions discrètes.
- Navigation principale stable : Accueil / Continuer, Recherche, Ma bibliothèque, Téléchargements, Statistiques, Paramètres.
- Pas de surcharge d'informations ni d'effets décoratifs inutiles ; les contrôles avancés restent accessibles quand on en a besoin.
- Le lecteur vidéo doit être encore plus minimaliste : vidéo centrale, commandes discrètes au survol, raccourcis évidents et boutons ±15 s.
- Le logo approuvé est `docs/branding/aniflow-logo-final.png` : un torii blanc, une petite bibliothèque/livre ouvert et un bouton lecture bleu électrique sur fond bleu marine très foncé. Le conserver comme référence de marque ; ne pas le remplacer par un logo différent sans demande explicite. Prévoir des variantes de taille/fond si nécessaire, en conservant le symbole simple et sa palette. Utiliser des icônes vectorielles quand possible et vérifier la lisibilité du logo à petite taille.
- Concevoir une interface adaptable aux résolutions courantes de Windows 11, y compris 1920×1080 et les fenêtres redimensionnées.

## 12. Architecture recommandée

- **Python + PySide6** : application de bureau et interface.
- **SQLite** : base locale pour les œuvres, relations, ordres personnalisés, fichiers, tâches de téléchargement, progression, sessions, statuts et paramètres.
- **AniList GraphQL** : source initiale de métadonnées, avec cache et gestion des limites.
- **MPV/libmpv** : option privilégiée pour le moteur vidéo, à valider techniquement en amont.
- **FFmpeg/ffprobe** : examiner les médias locaux, les pistes, les durées et les caractéristiques, selon la licence et le mode de distribution retenus.
- **Adaptateurs de téléchargement** : réutiliser des bibliothèques existantes pour les sources prises en charge au lieu de réécrire tous les extracteurs.
- **Ollama + modèle local** : intégration obligatoire pour toute fonctionnalité qui utilise de l’IA ; aucun fournisseur cloud ni mécanisme de repli distant. Les fonctionnalités non-IA ne doivent pas appeler le modèle par défaut.
- **Tests automatisés ciblés** : logique d'ordre, migrations SQLite, chronomètre, reprise de tâches et détection de fichiers.

Séparation logique minimale : `ui/`, `services/anilist/`, `services/watch_order/`, `services/player/`, `services/downloads/`, `services/intro_detection/`, `services/ai/`, `database/`, `statistics/`, `tests/`.

Éviter une architecture excessivement abstraite : chaque service doit exister pour un besoin réel et disposer d'une interface simple.

## 13. Données, confidentialité et robustesse

- Toutes les progressions et préférences doivent survivre au redémarrage.
- Prévoir une copie de sauvegarde et une restauration de la base SQLite.
- Ne pas enregistrer de secrets dans le dépôt GitHub. Ignorer `.env`, bases personnelles, logs volumineux, caches, vidéos, modèles et environnements virtuels.
- Les fonctions locales ne doivent pas envoyer l'historique de visionnage à une IA ou à un serveur sans action et information explicites.
- Protéger l'interface contre des noms de fichiers/URLs mal formés et valider les chemins choisis.
- Toute action destructive nécessite une confirmation explicite.

## 14. Critères d'acceptation du logiciel livré

1. Une recherche AniList affiche des résultats et gère les erreurs de réseau.
2. Une série peut être enregistrée localement et retrouvée après redémarrage.
3. L'ordre complet rassemble tous les contenus découverts, récapitulatifs compris ; un glisser-déposer permet de les réordonner et les placements incertains restent visibles.
4. Le bouton Suivant enchaîne correctement les éléments d'une file de visionnage personnalisée.
5. Les fichiers locaux peuvent être associés à une œuvre et lus dans le lecteur.
6. La lecture en pause n'augmente pas le temps réellement regardé ; la progression est restaurée après redémarrage.
7. Le statut À revoir et le compteur de re-visionnages sont persistants.
8. Les statistiques distinguent données mesurées et estimations historiques.
9. La file de téléchargement et le chemin des fichiers sont persistants ; la reprise après redémarrage fonctionne sur au moins une source de test compatible.
10. La détection de générique fonctionne sur un jeu de fichiers de test connu et indique clairement les cas incertains.
11. Toutes les fonctionnalités déclarées terminées ont un résultat de test réel consigné.
12. Les fonctions IA utilisent uniquement le modèle local configuré et ne peuvent pas appeler de service cloud ou basculer vers un fournisseur distant.
13. Une URL de média directe peut être ajoutée comme source lorsque son téléchargement est compatible ; un fichier vidéo peut toujours être associé manuellement.

## 15. Plan de livraison

Voir `ROADMAP.md`. L'objectif est le logiciel complet défini dans ce cahier des charges. Le travail doit être réalisé par phases compartimentées et livrables vérifiables, sans réduire la cible à un prototype jetable ni ignorer des fonctions attendues. Des versions internes et des commits intermédiaires sont encouragés, mais l'architecture doit anticiper l'ensemble des fonctionnalités. Toute fonctionnalité est déclarée terminée uniquement après les tests pertinents et un compte rendu exact.
