<img src="stack/portal/logo.svg" alt="" width="72">

# StartKit — La Suite numérique en local

StartKit fait tourner les applications de La Suite numérique sur ta machine : un portail pour les retrouver, un seul compte pour toutes, une seule commande pour tout lancer.

Ce guide va du démarrage à l'utilisation de chaque application. Les détails techniques sont à la fin, dans « Pour les développeurs ».

## Sommaire

1. [Démarrer StartKit](#1-démarrer-startkit)
2. [Créer un compte](#2-créer-un-compte)
3. [Se connecter et se déconnecter](#3-se-connecter-et-se-déconnecter)
4. [Utiliser les applications](#4-utiliser-les-applications)
5. [Lire les e-mails envoyés (Mailpit)](#5-lire-les-e-mails-envoyés-mailpit)
6. [Administrer](#6-administrer)
7. [Arrêter, relancer, repartir de zéro](#7-arrêter-relancer-repartir-de-zéro)
8. [En cas de problème](#8-en-cas-de-problème)
9. [Pour les développeurs](#9-pour-les-développeurs)

---

## 1. Démarrer StartKit

**Il te faut :** Docker avec Docker Compose, environ 8 Go de RAM libres et 10 Go de disque. Chrome ou Firefox.

Depuis le dossier `StartKit/` :

```bash
docker compose up -d
```

Le premier lancement télécharge les images (environ 3 Go) et prépare les bases : compte quelques minutes. Les suivants prennent environ une minute.

Ouvre ensuite **http://startkit.localhost:8000** : c'est la page de présentation de StartKit Afrique. Le bouton **Accéder à mon espace** mène au portail des applications, **http://startkit.localhost:8000/espace/**.

Le portail affiche une carte par application avec un voyant :

- **En ligne** : l'application répond, tu peux l'ouvrir.
- **Hors ligne ou en démarrage** : attends une minute ; si ça dure, voir [En cas de problème](#8-en-cas-de-problème).

Toutes les adresses en `*.localhost` marchent sans rien configurer. Les applications ne sont accessibles que depuis ta machine.

## 2. Créer un compte

### Où créer les comptes : dans Keycloak, nulle part ailleurs

Les comptes se créent **dans Keycloak** (http://auth.localhost:8000/admin, royaume **startkit**). C'est l'annuaire central de StartKit : la page « Connectez-vous à votre compte » que tu vois en te connectant, c'est lui.

**On ne crée pas de compte dans Docs, Visio, Fichiers, Grist, Transfers, Messages, Projets ou l'Assistant IA.** Elles n'ont pas de formulaire d'inscription : toutes délèguent la connexion à Keycloak. À la première connexion d'un compte, chaque application crée toute seule son profil (nom, e-mail) à partir de Keycloak.

```
                  ┌──────────────────────────────┐
  tu crées  ───▶  │  Keycloak (royaume startkit) │  ◀── un seul compte, un seul mot de passe
  le compte ici   └──────────────┬───────────────┘
                                 │ connexion unique
     ┌──────┬────────┬───────────┼──────────┬───────────┬──────────┐
     ▼      ▼        ▼           ▼          ▼           ▼          ▼
   Docs   Visio   Fichiers     Grist    Transfers   Messages   Projets
         (profil créé automatiquement à la première connexion)
```

| Application | Où vient le compte | À la première connexion |
| --- | --- | --- |
| Docs, Visio, Fichiers, Transfers, Assistant IA | Keycloak | le profil est créé automatiquement |
| Grist | Keycloak (e-mail **vérifié** obligatoire) | le compte rejoint l'espace d'équipe |
| Messages | Keycloak (e-mail en `@startkit.localhost` obligatoire) | la boîte `identifiant@startkit.localhost` est créée |
| Projets | Keycloak | le compte est créé ; tout le monde peut créer des projets |
| **Tchap** | **à part**, dans le service de comptes de Tchap (MAS) | voir [Compte Tchap](#compte-tchap) |

Deux façons de créer un compte Keycloak : le script `nouveau-compte.sh` (le plus simple) ou la console Keycloak, toutes deux décrites ci-dessous.

### Comptes déjà prêts

| Identifiant | Mot de passe | Nom affiché | Particularité |
| --- | --- | --- | --- |
| `user1` | `user1` | Camille Martin | administrateur de Projets et de Grist |
| `user2` | `user2` | Alex Bernard | — |
| `user3` | `user3` | Sacha Petit | — |

Tu peux te connecter avec l'identifiant ou avec l'e-mail (`user1@startkit.localhost`).

### Créer un compte en une commande

```bash
./nouveau-compte.sh alice Alice Durand
```

Le script crée l'identifiant `alice`, l'e-mail `alice@startkit.localhost` et le mot de passe `alice` (par défaut, le même que l'identifiant). Pour choisir le mot de passe, ajoute-le à la fin :

```bash
./nouveau-compte.sh alice Alice Durand MonMotDePasse
```

Le compte est utilisable tout de suite dans toutes les applications. Sa boîte Messages `alice@startkit.localhost` est créée à sa première connexion à Messages.

### Créer un compte à la main (console Keycloak)

1. Ouvre **http://auth.localhost:8000/admin** et connecte-toi avec `admin` / `admin`.
2. En haut à gauche, choisis le royaume **startkit** (et non « master »).
3. Menu **Utilisateurs**, puis **Créer un utilisateur**.
4. Remplis l'identifiant, le prénom, le nom et l'e-mail en **`@startkit.localhost`**.
5. Coche **E-mail vérifié**. Sans cette case, Grist refuse la connexion.
6. Clique sur **Créer**.
7. Onglet **Identifiants**, puis **Définir le mot de passe**. Décoche **Temporaire** si tu ne veux pas qu'on te demande d'en changer à la première connexion.

> **Pourquoi `@startkit.localhost` ?** Messages ne crée une boîte que pour les e-mails de ce domaine. Avec une autre adresse, le compte marche partout sauf dans Messages.

Dans la même console, tu peux aussi changer un mot de passe (onglet **Identifiants**), désactiver ou supprimer un compte.

### Compte Tchap

Tchap utilise sa propre connexion. Un compte est déjà prêt : `test@tchap.localhost` / `password`.

Pour en créer un autre, l'e-mail doit finir par `@tchap.localhost` :

```bash
docker exec mas-local mas-cli -c /config.yaml manage register-user --yes \
  -p MonMotDePasse -e bob@tchap.localhost -d "Bob Martin" bob
```

## 3. Se connecter et se déconnecter

1. Depuis le portail, ouvre une application.
2. Clique sur **Se connecter** (dans certaines applications, le bouton s'appelle **S'identifier avec ProConnect**).
3. La page « Connectez-vous à votre compte » de StartKit s'affiche : saisis ton identifiant et ton mot de passe.
4. Tu reviens dans l'application, connecté.

Ensuite, les autres applications te reconnaissent sans redemander le mot de passe : c'est la connexion unique. Dans certaines, il faut quand même cliquer une fois sur **Se connecter**.

**Se déconnecter :** utilise le menu de ton profil dans l'application. Pour fermer la session de toutes les applications d'un coup, ouvre http://auth.localhost:8000/realms/startkit/protocol/openid-connect/logout et confirme.

**Tester à plusieurs** (par exemple user1 qui partage un document avec user2) : connecte le second compte dans une fenêtre de navigation privée ou dans un autre navigateur.

## 4. Utiliser les applications

### Assistant IA — poser des questions à une IA locale

http://assistant.localhost:8000

1. Connecte-toi (la session ouverte dans une autre application suffit).
2. Tape ta question dans « Entrez votre message ou une question », puis Entrée.
3. La réponse s'affiche au fur et à mesure. Tes conversations sont listées à gauche ; **Nouvelle conversation** en démarre une autre.
4. Si plusieurs modèles sont proposés, choisis-le dans le sélecteur sous la zone de saisie.

Le modèle tourne **sur cette machine**, dans Ollama : les questions et les réponses ne sont envoyées à aucun service externe.

À savoir :

- Le modèle par défaut, **Qwen2.5 1.5B** (licence Apache 2.0), est petit pour tenir en mémoire à côté de toute la stack. Il répond vite (environ 10 mots par seconde sans carte graphique) mais **peut se tromper ou inventer** : c'est une démonstration, pas un outil de production.
- **Mistral 7B** (licence Apache 2.0), plus fiable, est aussi proposé. Il demande 4,5 Go de RAM libres : arrête d'abord ce que tu n'utilises pas, par exemple Tchap (`docker compose stop web`).
- L'envoi de documents à l'assistant et la recherche web sont désactivés.

### Docs — écrire à plusieurs

http://docs.localhost:8000

1. Clique sur **Nouveau** (en haut du menu de gauche ; à la première connexion, passe d'abord la présentation avec **Passer**).
2. Donne un titre, puis écris. Tape `/` pour insérer un titre, une liste, un tableau, une image…
3. Pour inviter quelqu'un, clique sur **Partager** et saisis son e-mail (par exemple `user2@startkit.localhost`). L'invitation arrive dans [Mailpit](#5-lire-les-e-mails-envoyés-mailpit).
4. Ouvre le même document avec un autre compte : vous voyez chacun les modifications de l'autre en direct.

Les documents peuvent contenir des sous-pages, pour former une arborescence.

**IA dans Docs :** sélectionne un passage, puis ouvre le menu IA de la barre de mise en forme pour le résumer, le corriger, le reformuler ou le traduire. Le traitement est fait par le modèle local, comme pour l'Assistant IA (voir ci-dessous) ; compte 10 à 20 secondes.

### Visio — visioconférence

http://visio.localhost:8000

1. Clique sur **Créer une réunion**, puis **Démarrer une réunion instantanée**, ou **Créer une réunion pour une date ultérieure** pour obtenir un lien à partager.
2. Autorise la caméra et le micro quand le navigateur le demande.
3. Clique sur **Copier le lien** et envoie-le aux participants. Les personnes qui ont le lien peuvent rejoindre la réunion.

À savoir : la visio ne fonctionne qu'entre navigateurs de **cette machine** (plusieurs onglets ou fenêtres). L'enregistrement des réunions est désactivé par défaut.

### Fichiers — stocker et partager

http://fichiers.localhost:8000

1. Clique sur **Nouveau** pour importer des fichiers ou un dossier, ou pour créer un dossier.
2. Clique sur un fichier pour l'aperçu ; le menu de chaque élément permet de le télécharger, le renommer, le partager ou le supprimer.
3. Pour partager, ajoute l'e-mail d'un autre compte : le fichier apparaît dans son onglet **Partagés avec moi**.

Les éléments supprimés vont dans la **Corbeille**. Certains types de fichiers sont refusés à l'import (liste blanche). L'édition en ligne des documents bureautiques n'est pas activée.

### Grist — tableur et bases de données

http://grist.localhost:8000

1. Clique sur **Document vide**, ou **Importer un fichier** pour partir d'un fichier CSV ou Excel.
2. Saisis tes données ; chaque colonne a un type (texte, nombre, date, référence…) et peut contenir une formule.
3. Ajoute des tables et des vues (fiches, graphiques) avec le bouton **Ajouter**, en haut à gauche.
4. L'icône de partage, en haut à droite, donne accès à d'autres comptes avec des droits propriétaire, éditeur ou lecteur.

Tous les comptes partagent le même espace d'équipe. `user1` en est le propriétaire et l'administrateur de l'instance.

### Transfers — envoyer des fichiers volumineux

http://transfers.localhost:8000

1. Connecte-toi. Dans **Créer un nouveau transfert**, clique sur la zone de dépôt ou glisses-y tes fichiers.
2. Choisis le mode de partage :
   - **Courriel** : saisis les adresses dans **Envoyer à** ; les destinataires reçoivent un message (visible dans Mailpit) ;
   - **Lien** : tu obtiens un lien à transmettre toi-même.
3. Donne un **Titre** et choisis la **Durée de validité** (1, 7 ou 30 jours). Dans **Options avancées**, le mode confidentiel place la clé de déchiffrement dans le lien lui-même : sans le lien complet, personne ne peut lire les fichiers.
4. Clique sur **Envoyer**. Le destinataire ouvre le lien et télécharge **sans avoir de compte**.

Les fichiers sont chiffrés dans ton navigateur avant l'envoi. Limites : 20 fichiers et 20 Go par transfert. Ton tableau de bord liste tes transferts ; tu peux les désactiver ou renvoyer l'invitation.

### Messages — boîte mail collaborative

http://messages.localhost:8000

Chaque compte a sa boîte `identifiant@startkit.localhost`.

- **Écrire à un autre compte StartKit** (par exemple `user2@startkit.localhost`) : le message arrive directement dans sa boîte Messages.
- **Écrire à une autre adresse** (par exemple `quelquun@example.com`) : le message ne part pas sur Internet ; il est capturé dans [Mailpit](#5-lire-les-e-mails-envoyés-mailpit).
- **Recevoir un e-mail « de l'extérieur »** : envoie-le au serveur SMTP local, port 2525 :

  ```bash
  python3 -c 'import smtplib; from email.message import EmailMessage as M; m=M(); m["From"]="test@example.com"; m["To"]="user1@startkit.localhost"; m["Subject"]="Test"; m.set_content("Bonjour"); smtplib.SMTP("localhost",2525).send_message(m)'
  ```

Messages range les échanges en fils de discussion. La recherche porte sur tout le contenu des messages.

### Projets — tableaux kanban

http://projects.localhost:8000

1. Connecte-toi avec **S'identifier avec ProConnect**.
2. Crée un projet, puis un tableau dans ce projet.
3. Ajoute des listes (par exemple « À faire », « En cours », « Fait ») puis des cartes ; fais glisser les cartes d'une liste à l'autre.
4. Ouvre une carte pour ajouter une description, des étiquettes, une échéance, des pièces jointes ou des membres.
5. Invite d'autres comptes dans les membres du projet.

`user1` est administrateur. Les notifications par e-mail arrivent dans Mailpit.

### Tchap — messagerie instantanée

http://localhost:8088

1. Clique sur **Se connecter** et saisis `test@tchap.localhost`.
2. Connecte-toi avec le mot de passe `password`.
3. Crée un salon ou une conversation, puis invite d'autres comptes Tchap (voir [Compte Tchap](#compte-tchap)).

Le front Tchap tourne en mode développement : le premier chargement peut prendre une minute.

## 5. Lire les e-mails envoyés (Mailpit)

http://mail.localhost:8000

Aucune application n'envoie de vrai e-mail : invitations Docs, partages, transferts, notifications de Projets et messages Messages vers l'extérieur arrivent tous dans **Mailpit**. Clique sur un message pour le lire et suivre ses liens.

## 6. Administrer

| Quoi | Adresse | Identifiants |
| --- | --- | --- |
| Comptes et connexion (Keycloak) | http://auth.localhost:8000/admin, royaume **startkit** | `admin` / `admin` |
| Admin Docs, Visio, Messages, Fichiers, Transfers, Assistant IA | `http://<app>.localhost:8000/admin` | `admin@startkit.localhost` / `admin` |
| Admin Grist | menu du profil de `user1`, **Panneau d'administration** | compte `user1` |
| Stockage des fichiers (S3) | http://s3-console.localhost:8000 | `startkit` / `startkit-secret` |

L'admin Django de chaque application permet de voir et modifier ses données. Exemple : dans Messages, gérer les domaines et les boîtes, ou donner à un utilisateur des droits sur une boîte partagée.

## 7. Arrêter, relancer, repartir de zéro

```bash
docker compose stop           # tout arrêter, les données sont conservées
docker compose up -d          # tout relancer
docker compose ps             # voir l'état de chaque conteneur
docker compose down           # supprimer les conteneurs, les données sont conservées
docker compose down -v        # tout supprimer, y compris comptes, documents et fichiers
```

Après un `down -v`, le prochain `up -d` recrée une installation neuve avec les comptes `user1` à `user3`. Les comptes créés depuis sont perdus.

## 8. En cas de problème

| Symptôme | Que faire |
| --- | --- |
| Une carte reste « Hors ligne » sur le portail | `docker compose ps`, puis `docker compose logs <service>` (par exemple `docs-backend`). Relance avec `docker compose up -d`. |
| « Identifiant ou mot de passe invalide » | Vérifie le compte dans la console Keycloak, royaume **startkit**. Les mots de passe des comptes de test sont égaux à l'identifiant. |
| Grist refuse la connexion d'un nouveau compte | Coche **E-mail vérifié** sur ce compte dans Keycloak. |
| Messages refuse un nouveau compte | Son e-mail doit finir par `@startkit.localhost`. |
| La caméra ou le micro ne marchent pas dans Visio | Autorise-les dans le navigateur (icône à gauche de l'adresse). |
| Je suis connecté avec le mauvais compte | Déconnecte-toi (voir [section 3](#3-se-connecter-et-se-déconnecter)) ou utilise une fenêtre privée. |
| Tchap reste sur une page blanche | Suis le démarrage avec `docker compose logs -f web`. S'il reste sur « Waiting for … in another nx process », arrête `web`, renomme `tchap/tchap-web-v4/.nx/workspace-data`, puis relance `docker compose up -d web`. |
| L'Assistant IA répond par une erreur | Le modèle choisi ne tient peut-être pas en mémoire. Repasse sur Qwen2.5 1.5B, ou libère de la RAM. Vérifie qu'Ollama tourne : `curl localhost:11434/api/tags`. |
| La machine rame | StartKit utilise 7 à 8 Go de RAM. Arrête ce que tu n'utilises pas, par exemple `docker compose stop web` pour Tchap. |

---

## 9. Pour les développeurs

### Organisation

```
compose.yml                  point d'entrée : inclut tous les fichiers ci-dessous
nouveau-compte.sh            crée un compte Keycloak en une commande
stack/infra.yml              proxy Caddy, Keycloak, PostgreSQL, Redis, S3, Mailpit
stack/apps/<app>.yml         services de chaque application (images officielles)
stack/env/<app>.env          configuration de chaque application
stack/caddy/Caddyfile        routage *.localhost:8000 (+ stack/caddy/apps/*.caddy)
stack/keycloak/…realm.json   royaume « startkit » : clients et comptes de test
stack/postgres/init.sql      une base par application
stack/portal/                landing page (index.html), portail des applications (espace/) et logo
tchap/tchap-local-stack/     la stack Tchap, incluse telle quelle
suitenumerique*/             clones des forks (remote « upstream » = dépôt officiel)
```

- **Un seul proxy sur le port 8000.** Il a des alias réseau (`auth.localhost`, `docs.localhost`…), donc les conteneurs joignent les mêmes URL que le navigateur. C'est ce qui rend l'OIDC fiable.
- **Infrastructure partagée :** une base PostgreSQL et un préfixe Redis par application, un seul Keycloak et un seul S3.
- **Images officielles épinglées :** Docs v6.0.4, Visio v1.37.0, Messages 0.10.0, Projets 1.27.13, Fichiers v0.26.0, Grist 1.7.22, Transfers 0.5.2, Conversations (Assistant IA) v0.0.28.
- **HTTP simple :** les configurations Django `Production` forcent HTTPS, donc chaque app Django charge une petite classe `Http(Production)` injectée par compose (`configs:`).
- Les migrations (`*-migrate`) sont rejouées à chaque `up` ; elles sont idempotentes.
- Le fichier du royaume n'est importé qu'au premier démarrage de Keycloak. Pour ajouter un client à une installation existante, crée-le aussi dans la console (ou avec `kcadm.sh`).

### Développer une application depuis son fork

1. Arrête sa version « image », par exemple `docker compose stop docs-frontend docs-backend docs-celery`.
2. Lance-la en mode développement depuis son clone, avec ses propres commandes (`make bootstrap`, `make run`…) et ses ports par défaut.

Pour garder les forks à jour :

```bash
gh repo sync GNAOLinus/suitenumerique-meet               # côté GitHub
git -C suitenumerique-meet pull --rebase upstream main   # côté clone
```

### Page d'accueil

- `stack/portal/index.html` est la page de présentation de StartKit Afrique ; `stack/portal/espace/index.html` est le portail des applications.
- Les boutons « Demander une démo » utilisent les coordonnées déclarées en bas du fichier `index.html`, dans l'objet `CONTACT` (`email`, `whatsapp`). Tant qu'elles sont vides, ils mènent au prototype.
- La page n'utilise aucune ressource externe (polices, images, scripts) : elle fonctionne hors ligne.

### IA locale

- Les modèles tournent dans **Ollama, installé sur la machine hôte** (port 11434, écoute sur `127.0.0.1` uniquement).
- Le service `ollama-relay` (`stack/apps/ia.yml`) le rend joignable depuis les conteneurs seulement, sur l'adresse du pont Docker `172.17.0.1`. Les services l'appellent via `http://host.docker.internal:11434/v1`, une API compatible OpenAI.
- Les modèles de l'Assistant IA sont déclarés dans `stack/conversations/llm-configuration.json` ; celui de Docs dans `AI_MODEL` (`stack/env/docs.env`).
- Pour ajouter un modèle : `ollama pull <modèle>`, puis déclare-le dans ces fichiers et relance `docker compose up -d conversations-backend docs-backend`.
- Seule sortie réseau : au premier comptage de jetons, l'Assistant télécharge le fichier de découpage de texte `cl100k_base` (1,7 Mo, aucune donnée utilisateur). Hors ligne, il utilise une estimation.

### Options désactivées par défaut

- **Enregistrement des réunions Visio** : `docker compose --profile recording up -d`, puis `RECORDING_ENABLE=True` dans `stack/env/meet.env` (environ 2 Go de RAM en plus).
- **Transcription et résumé des réunions Visio** : non inclus, ils demandent WhisperX.
- **Assistant BlockNote dans Docs** (modules « XL », sous licence GPL) : désactivé ; seules les actions IA du menu sont actives.
- **« Éditer dans Docs » depuis l'Assistant IA** : désactivé (il faudrait configurer Docs en serveur de ressources OIDC).
- **Édition bureautique en ligne dans Fichiers** (Collabora, environ 1,5 Go de RAM) : la marche à suivre est en tête de `stack/apps/drive.yml`.
- **Recherche Messages** : OpenSearch tourne avec 512 Mo de tas. Pour l'enlever, voir les commentaires de `stack/apps/messages.yml`.
# startkit
