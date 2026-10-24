# Création et réglages recommandés du dépôt GitHub AniFlow

## Paramètres du dépôt

À créer sur GitHub avec les valeurs suivantes :

- **Repository name :** `AniFlow`
- **Description :** `Application Windows de bibliothèque, chronologie et lecteur d’animés`
- **Visibility :** `Private` (recommandé tant que le projet et les licences ne sont pas prêts pour une publication)
- **Add README :** non si tu suis les étapes « dépôt vide » ci-dessous, car le kit contient déjà `README.md`
- **Add .gitignore :** aucun lors de la création, car le kit contient déjà un `.gitignore` adapté
- **Choose a license :** aucune pour le moment ; choisis une licence seulement quand la politique de distribution et les licences des composants auront été décidées
- **Default branch :** `main`

Un dépôt privé peut devenir public plus tard, mais vérifier d'abord les secrets, historiques de commits, médias, modèles et licences.

## Méthode simple avec GitHub + GitHub Desktop

1. Crée un dépôt vide privé `AniFlow` sur GitHub (sans README, sans .gitignore, sans licence).
2. Installe/ouvre GitHub Desktop et connecte-toi à GitHub.
3. Dans GitHub Desktop, clone `AniFlow` sur ton PC Windows dans un dossier simple, par exemple `C:\Dev\AniFlow`.
4. Décompresse `AniFlow_Planning_v0.4.zip` dans un dossier temporaire. Copie **le contenu** du dossier extrait (fichiers `README.md`, `SPEC.md`, `PROJECT_STATUS.md`, etc. et le dossier `docs`) à la racine du dépôt cloné ; ne copie pas un dossier `AniFlow_Planning_v0.4` supplémentaire imbriqué.
5. Vérifie que `.gitignore` est présent et que `docs/branding/aniflow-logo-final.png` existe.
6. Dans GitHub Desktop, vérifie la liste des changements. Le premier commit peut s'appeler `docs: add AniFlow specification and workflow`.
7. Publie/pousse ce commit vers le dépôt privé. Vérifie sur github.com que les fichiers et le logo s'affichent.

Alternative : si tu préfères créer le dépôt directement depuis GitHub Desktop, crée le dépôt local dans le dossier où se trouvent déjà les fichiers, en utilisant le .gitignore fourni et sans ajouter de licence, puis publie-le en privé. Évite de créer deux README/.gitignore concurrents.

## Réglages GitHub après création

- Garde le dépôt **Private** pour le moment.
- Ne place aucune clé, aucun token, fichier `.env`, historique personnel SQLite, vidéo, modèle IA, fichier de configuration contenant des secrets ou gros cache dans le dépôt.
- Active la vérification en deux étapes de ton compte GitHub.
- N'active pas GitHub Pages : AniFlow est une application Windows, pas un site web à publier.
- Ne configure pas tout de suite d'action GitHub qui appelle une API Claude payante. Le suivi Git doit d'abord être manuel et transparent.
- Laisse les GitHub Actions désactivées/non configurées jusqu'à ce que les dépendances et tests du projet existent. Ensuite, Claude pourra ajouter une CI simple qui installe les dépendances et exécute les tests pertinents.
- Utilise `main` pour les états stables. Pour les gros changements, crée une branche `feature/nom-court`, teste, puis fusionne quand tu as examiné les changements.
- Les règles de protection de `main` sont facultatives à cette étape. Selon le plan GitHub, certaines protections des dépôts privés peuvent ne pas être disponibles ; ne bloque pas le projet à cause de cela.
- Ne publie pas le dépôt tant que les licences des dépendances, le droit de distribution et les éventuels secrets n'ont pas été vérifiés.

## Connecter le dépôt à Claude

### Si tu utilises Claude.ai (intégration de contexte GitHub)

1. Dans Claude, connecte GitHub via les paramètres/connexions ou le bouton d'ajout de contenu.
2. Autorise seulement le dépôt `AniFlow` si GitHub te permet de choisir les dépôts accessibles.
3. Ajoute au projet Claude les fichiers de référence : `CLAUDE_MASTER_PROMPT.md`, `PROJECT_STATUS.md`, `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `CLAUDE_WORKFLOW.md` et `README.md`.
4. Synchronise le dépôt avant une session importante après avoir modifié des fichiers.
5. **Important :** l'intégration de contexte GitHub peut lire les fichiers sélectionnés, mais ne transmet pas l'historique des commits ou les pull requests et ne signifie pas automatiquement que Claude peut modifier le dépôt. Vérifie ce que l'environnement permet. Avec le simple chat, applique les fichiers/patchs produits par Claude dans le dépôt local puis fais un commit avec GitHub Desktop.

### Si tu utilises un environnement de code ayant accès au dépôt local

Ouvre le dossier cloné `C:\Dev\AniFlow` dans cet environnement, vérifie qu'il peut lire et modifier les fichiers et lancer les commandes. Donne-lui `CLAUDE_MASTER_PROMPT.md`. Ne donne pas de token GitHub dans le prompt ni dans un fichier versionné. Vérifie chaque diff et résultat avant d'envoyer les modifications vers le dépôt distant.

## Branches, commits et sauvegarde

- `main` : état stable.
- `feature/...` : gros bloc de fonctionnalité ou phase en cours.
- Messages de commit explicites : `feat: add AniList search`, `fix: preserve watch order`, `docs: update project status`.
- Commit après un bloc cohérent vérifié, pas après chaque ligne.
- `PROJECT_STATUS.md` contient le dernier commit stable et la prochaine tâche.
- GitHub conserve l'historique du code et des documents, mais **ne sauvegarde pas** les vidéos, modèles IA ou la base locale grâce au `.gitignore`. Sauvegarde séparément la base personnelle de l'application lorsqu'elle existera.

## Ne pas confondre archivage documentaire et archivage GitHub

Si `DEV_LOG.md` devient trop long, déplacer les anciennes entrées vers `docs/archive/DEV_LOG_...md`. **Ne clique pas sur “Archive repository” dans les paramètres GitHub** : cela rendrait le dépôt en lecture seule et ce n'est pas le but.
