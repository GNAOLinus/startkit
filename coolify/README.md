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
| Domaine | `web.niyiexpertise.com` (ou un domaine dont tu contrôles le DNS) |
| DNS | `*.web.niyiexpertise.com` → IP du serveur, ou un enregistrement par sous-domaine |
| Ports | 80/443 (Coolify), **7881/tcp et 7882/udp** (média Visio), 8000 non exposé publiquement |
| Coolify | une instance fonctionnelle, avec accès au dépôt `startkit` |

> Le port `8000` du service `proxy` ne doit **pas** être ouvert sur Internet : Coolify
> route le trafic vers ce port en interne, c'est lui qui gère le TLS.

---

## Configuration et secrets automatiques

Le déploiement Coolify n'a besoin ni de SSH, ni de script de préparation, ni d'un fichier
`.env` à copier. Le Compose référence les variables secrètes générées par Coolify
(`SERVICE_PASSWORD_*`), qui sont conservées entre les déploiements. Les services
`config-init` et `proxy` construisent leurs images depuis le dépôt ; le premier
rend les fichiers Keycloak, PostgreSQL et LiveKit à partir de ces secrets.
Les répertoires nécessaires sont copiés dans les images : l'option **Preserve
repository during deployment** n'est pas nécessaire.

Le domaine par défaut correspond à celui de ta capture :
`web.niyiexpertise.com` (portail `startkit.web.niyiexpertise.com`). Pour utiliser
un autre domaine, la variable `DOMAIN` peut être modifiée dans Coolify.

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

`compose.flat.yml` est **versionné** (Coolify le lit depuis Git). Les valeurs de
configuration viennent des gabarits suivis par Git et les secrets sont générés
à la première lecture du Compose ; les fichiers sensibles ne sont pas committés.
Pour une ressource Coolify déjà créée, après publication de ces changements,
cliquer une fois sur **Reload Compose** afin qu'elle charge le nouveau fichier.
Ensuite, seul **Deploy** sera nécessaire.

---

## 3. Créer la ressource dans Coolify

1. **+ New** → **Docker Compose** (dépôt Git `StartKit`).
2. **Base Directory** : `/`
3. **Docker Compose Location** : `/coolify/compose.flat.yml`
   (le fichier aplati et versionné, **pas** `/compose.yml` qui est celui du
   développement local, ni `/coolify/compose.yml` qui utilise `include:`).
4. **Environment Variables** : aucune variable à saisir. Coolify crée les
   valeurs `SERVICE_PASSWORD_*` référencées dans le Compose.
5. **Domains** : les ajouter sur le service **`proxy`**, port **8000**, un par URL
   (Coolify accepte une liste séparée par des virgules). Cette configuration est
   nécessaire une seule fois : le domaine `startkit.web.niyiexpertise.com` déjà
   présent dans ta ressource ne route pas à lui seul les autres sous-domaines.

```
https://startkit.web.niyiexpertise.com,https://docs.web.niyiexpertise.com,https://visio.web.niyiexpertise.com,https://livekit.web.niyiexpertise.com,
https://messages.web.niyiexpertise.com,https://projects.web.niyiexpertise.com,https://fichiers.web.niyiexpertise.com,
https://grist.web.niyiexpertise.com,https://transfers.web.niyiexpertise.com,https://assistant.web.niyiexpertise.com,
https://auth.web.niyiexpertise.com,https://mail.web.niyiexpertise.com,https://s3.web.niyiexpertise.com,https://s3-console.web.niyiexpertise.com
```

6. **Persistent Storage** : ne rien ajouter, les volumes `postgres-data`, `s3-data`
   et les volumes applicatifs sont déclarés dans le compose et conservés par Docker.
7. Cliquer sur **Deploy**. Après cette configuration initiale, les déploiements
   suivants se font avec **Deploy** uniquement.

> Le fichier aplati ne contient plus `include:` : Coolify liste donc bien tous les
> services actifs (42 ; `meet-egress` est derrière le profil `recording`). Aucun
> réglage « raw compose » n'est nécessaire.

---

## 4. Après le premier déploiement

| Vérification | Commande / URL |
|---|---|
| Portail | `https://startkit.web.niyiexpertise.com` |
| Connexion unique | `https://auth.web.niyiexpertise.com` (comptes `user1`/`user2`/`user3`) |
| Console Keycloak | `https://auth.web.niyiexpertise.com/admin` (`admin` + mot de passe généré dans les variables Coolify) |
| Média Visio | ouvrir une visio à deux, depuis deux réseaux différents (teste réellement 7881/7882) |
| Résolution interne | `docker exec "$(docker ps -qf name=docs-backend)" curl -sI https://auth.web.niyiexpertise.com/realms/startkit \| head -1` doit répondre `200`/`302` |

**Point critique — résolution interne.** Les conteneurs joignent Keycloak par son
URL publique (`https://auth.web.niyiexpertise.com`). Cela suppose que le serveur puisse
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
  `https://mail.web.niyiexpertise.com`. Pour envoyer de vrais e-mails, remplacer les
  variables `DJANGO_EMAIL_*` de `coolify/templates/env/*.env` par un SMTP réel
  (et le `smtpServer` du realm pour Keycloak).
- **Comptes de démo** : leurs mots de passe sont générés par Coolify dans les
  variables `SERVICE_PASSWORD_64_DEMOPASSWORDUSER1` (et `DEMOPASSWORDUSER2`, `DEMOPASSWORDUSER3`).
  L'administrateur Keycloak est `admin` ; son mot de passe est dans
  `SERVICE_PASSWORD_64_KEYCLOAKADMINPASSWORD`.
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
  `node_ip: <IP publique>` dans `coolify/templates/livekit.yaml`, puis redéployer.
- **Mises à jour** : les images sont épinglées (versions des `stack/apps/*.yml`).
  Mettre à jour = changer le tag, régénérer `compose.flat.yml`
  (`python3 coolify/flatten.py`), puis redéployer. Les secrets existants sont
  conservés par Coolify.
