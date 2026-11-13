# Déploiement de StartKit sur Coolify

Cette variante déploie la même stack que `compose.yml`, mais :

- avec de **vrais domaines** (HTTPS terminé par le proxy de Coolify) ;
- avec des **secrets générés** (aucun mot de passe de développement) ;
- **sans Tchap** (sa stack locale tourne en mode développement) ;
- avec **Visio utilisable à distance** (ports média LiveKit ouverts) ;
- en conservant les **comptes de démonstration** `user1`, `user2`, `user3`.

Le fonctionnement local (`docker compose up -d`) n'est pas modifié.

---

## 1. Prérequis

| Élément | Détail |
|---|---|
| Serveur | 8 Go de RAM minimum (Postgres + Keycloak + 8 apps + LiveKit), 4 vCPU recommandés |
| Domaine | un domaine dont tu contrôles le DNS, par ex. `example.com` |
| DNS | `*.example.com` → IP du serveur (le plus simple), ou un enregistrement par sous-domaine (liste au §4) |
| Ports | 80/443 (Coolify), **7881/tcp et 7882/udp** (média Visio), 8000 non exposé publiquement |
| Coolify | une instance fonctionnelle, avec accès au dépôt `startkit` |

> Le port `8000` du service `proxy` ne doit **pas** être ouvert sur Internet : Coolify
> route le trafic vers ce port en interne, c'est lui qui gère le TLS.

---

## 2. Générer la configuration

La génération se fait **sur le serveur, dans le répertoire persistant de la
ressource** : `/data/coolify/applications/<uuid>/`.

C'est ce répertoire que Coolify monte (les volumes relatifs du compose y sont
résolus) et dans lequel il copie le dépôt à chaque déploiement lorsque
**Preserve repository during deployment** est activé. Les fichiers générés
(secrets, realm, init.sql, livekit.yaml) doivent donc y vivre, et non dans le
clone éphémère de déploiement.

```bash
# Sur le serveur. <uuid> = identifiant de la ressource (visible dans son URL).
DEST=/data/coolify/applications/<uuid>
mkdir -p "$DEST"
git clone https://github.com/GNAOLinus/startkit.git "$DEST"   # si le dossier est vide
cd "$DEST"

# 1. Renseigner le domaine (sans https:// ni slash final)
#    DOMAIN=example.com  ->  portail https://startkit.example.com
#                            Docs     https://docs.example.com
#                            etc.
bash coolify/prepare.sh          # crée coolify/coolify.env
$EDITOR coolify/coolify.env      # DOMAIN=example.com
bash coolify/prepare.sh          # génère stack/env/ et coolify/generated/
```

Le script affiche à la fin les URL et **tous les identifiants** (comptes de démo,
administrateur Django, administrateur Keycloak). Note-les : ils ne sont affichés
que là, même s'ils restent lisibles dans `coolify/coolify.env`.

Fichiers produits (non versionnés, donc conservés d'un déploiement à l'autre) :

```
coolify/coolify.env              # domaine + tous les secrets (chmod 600)
coolify/generated/startkit-realm.json
coolify/generated/livekit.yaml
coolify/generated/init.sql
coolify/generated/{proxy,infra,s3,keycloak}.env
coolify/generated/variables-coolify.env  # variables à coller dans Coolify (§3)
stack/env/*.env                  # configuration des 10 applications (dev local)
```

Relancer `prepare.sh` est sans danger : les secrets existants sont réutilisés.
Il refuse d'écraser `stack/env/*.env` s'il détecte la configuration locale
(domaines `.localhost`) ; utiliser `--force` en connaissance de cause.

### Fichier Compose réellement déployé

Coolify ne résout pas la clé `include:` : il ne lit qu'un seul fichier, puis le
réécrit avant `docker compose build`. Un fichier qui utilise `include:` est donc
vidé de ses services (d'où l'erreur `service "meet-livekit" has neither an image
nor a build context specified`). C'est pourquoi le dépôt contient
**`coolify/compose.flat.yml`**, version aplatie et autonome de
`coolify/compose.yml` (+ `coolify/infra.yml` + `stack/apps/*.yml`).

```bash
python3 coolify/flatten.py          # à relancer après toute modification des yml
python3 coolify/flatten.py --check  # échoue si compose.flat.yml est périmé
```

`compose.flat.yml` est **versionné** (Coolify le lit depuis Git). Il convertit
aussi chaque `env_file:` en `environment:` référençant des variables préfixées
(`MEET_DB_NAME`, `DOCS_DJANGO_SECRET_KEY`, …) : Coolify n'a qu'un jeu de variables
par ressource et écrase les `env_file:` des services par un `.env` commun, or les
fichiers d'environnement de StartKit partagent des clés avec des valeurs
différentes. Les valeurs sont dans `coolify/generated/variables-coolify.env`, à coller
dans Coolify (§3).

### Mise à jour de la configuration

`prepare.sh` lit `DOMAIN` depuis l'environnement s'il n'est pas dans
`coolify/coolify.env`, ce qui permet de ne rien stocker en clair dans cette
variable. Les *secrets*, eux, restent dans `coolify/coolify.env` (créé au premier
passage puis conservé, car ignoré par Git).

> **Ne pas utiliser *Pre-deployment Command*** pour lancer `prepare.sh` : cette
> commande s'exécute avec `docker exec` **dans un conteneur de l'application**,
> pas sur l'hôte ni dans le dépôt. Relancer `bash coolify/prepare.sh` à la main
> dans `/data/coolify/applications/<uuid>/` après une modification des gabarits,
> puis recoller `coolify/generated/variables-coolify.env` dans Coolify (§3).

---

## 3. Créer la ressource dans Coolify

1. **+ New** → **Docker Compose** (dépôt Git `StartKit`).
2. **Base Directory** : `/`
3. **Docker Compose Location** : `/coolify/compose.flat.yml`
   (le fichier aplati et versionné, **pas** `/compose.yml` qui est celui du
   développement local, ni `/coolify/compose.yml` qui utilise `include:`).
4. **General → Build pipeline → Preserve repository during deployment** :
   **activé**. Indispensable : les volumes montent des fichiers et dossiers du
   dépôt (`stack/caddy/...`, `stack/portal`, `coolify/generated/...`). Sans cette
   option, Coolify ne copie pas le dépôt dans le répertoire persistant et Docker
   crée des dossiers vides à la place des fichiers (`not a directory`).
5. **Environment Variables** : coller l'intégralité de
   `coolify/generated/variables-coolify.env` (produit par `prepare.sh`, jamais versionné).
   Ce fichier contient les ~470 variables préfixées par application ; tant
   qu'elles manquent, le déploiement s'arrête sur
   `required variable MEET_DB_NAME is missing a value` (le préfixe indique le
   fichier d'origine). À recoller après toute modification des gabarits
   `coolify/templates/**`, puis redéployer.
6. **Domains** : les ajouter sur le service **`proxy`**, port **8000**, un par URL
   (Coolify accepte une liste séparée par des virgules) :

```
https://startkit.example.com,https://docs.example.com,https://visio.example.com,
https://messages.example.com,https://projects.example.com,https://fichiers.example.com,
https://grist.example.com,https://transfers.example.com,https://assistant.example.com,
https://auth.example.com,https://mail.example.com,https://s3-console.example.com
```

7. **Persistent Storage** : ne rien ajouter, les volumes `postgres-data`, `s3-data`
   et les volumes applicatifs sont déclarés dans le compose et conservés par Docker.
8. Déployer.

> Le fichier aplati ne contient plus `include:` : Coolify liste donc bien tous les
> services actifs (40 ; `meet-egress` est derrière le profil `recording`) et génère
> les labels de domaine. Aucun réglage « raw compose » n'est nécessaire.

---

## 4. Après le premier déploiement

| Vérification | Commande / URL |
|---|---|
| Portail | `https://startkit.example.com` |
| Connexion unique | `https://auth.example.com` (comptes `user1`/`user2`/`user3`) |
| Console Keycloak | `https://auth.example.com/admin` (`admin` + mot de passe affiché par `prepare.sh`) |
| Média Visio | ouvrir une visio à deux, depuis deux réseaux différents (teste réellement 7881/7882) |
| Résolution interne | `docker exec "$(docker ps -qf name=docs-backend)" curl -sI https://auth.example.com/realms/startkit \| head -1` doit répondre `200`/`302` |

**Point critique — résolution interne.** Les conteneurs joignent Keycloak par son
URL publique (`https://auth.example.com`). Cela suppose que le serveur puisse
atteindre sa propre IP publique (cas normal sur un VPS). Sinon, les connexions
OIDC échouent avec des erreurs de type `Connection refused` / `Timeout` dans les
logs des backends.

**Keycloak et PostgreSQL n'importent qu'une seule fois.** Le realm (comptes de
démo) est importé au premier démarrage sur une base vide ; `init.sql` s'exécute
au premier démarrage du volume PostgreSQL. Pour repartir de zéro, supprimer les
volumes (`docker volume ls | grep -E 'postgres-data|s3-data'` puis
`docker volume rm <nom>`), ou repartir d'une ressource Coolify neuve.

---

## 5. Limites connues

- **E-mails** : la stack utilise mailpit (capture, aucun envoi réel), visible sur
  `https://mail.example.com`. Pour envoyer de vrais e-mails, remplacer les
  variables `DJANGO_EMAIL_*` de `coolify/templates/env/*.env` par un SMTP réel
  (et le `smtpServer` du realm pour Keycloak).
- **E-mails des comptes de démo** : `user1@startkit.<domaine>`. Modifier le gabarit
  du realm si tu veux un autre domaine.
- **Tchap** n'est pas inclus : `tchap/tchap-local-stack` (Dex/MAS/Synapse) est une
  stack de développement. Le déploiement en production demande une configuration
  séparée.
- **SMTP entrant de Messages** (`messages-mta-in`, port 2525 publié) : inutile sans
  enregistrement MX et sans le port 25 ; à retirer du compose pour un déploiement
  qui ne reçoit pas de courrier.
- **Grist/Conversations** utilisent une clé d'API `AI_PROVIDER_API_KEY` générée :
  brancher un vrai fournisseur LLM (Ollama, OpenAI, etc.) avant de s'en servir.
- **LiveKit derrière un NAT** : `use_external_ip: true` échoue si le serveur ne
  peut pas découvrir son IP publique ; dans ce cas, remplacer cette ligne par
  `node_ip: <IP publique>` dans `coolify/templates/livekit.yaml`.
- **Mises à jour** : les images sont épinglées (versions des `stack/apps/*.yml`).
  Mettre à jour = changer le tag, relancer `prepare.sh` si un gabarit change,
  régénérer `compose.flat.yml` (`python3 coolify/flatten.py`), recoller
  `coolify/generated/variables-coolify.env` si des clés ont changé, puis redéployer.
