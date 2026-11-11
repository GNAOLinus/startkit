#!/usr/bin/env bash
# Génère la configuration de déploiement distant de StartKit (Coolify).
#
#   bash coolify/prepare.sh            # crée/complete coolify/coolify.env puis rend les fichiers
#   bash coolify/prepare.sh --force    # idem, en écrasant une config locale de stack/env/
#
# Entrée  : coolify/coolify.env (créé au premier lancement, secrets générés)
# Sorties : stack/env/*.env, coolify/generated/{startkit-realm.json,livekit.yaml,
#           init.sql,infra.env,s3.env,keycloak.env,proxy.env}
#
# Ces fichiers ne sont pas versionnés. Relancer le script à chaque déploiement est
# sans danger : les secrets déjà présents dans coolify.env sont réutilisés.
set -euo pipefail

cd "$(dirname "$0")"
ROOT=$(cd .. && pwd)
ENV_FILE="coolify.env"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

cyan() { printf '\033[1;36m%s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m%s\033[0m\n' "$*" >&2; }
die()  { printf '\033[1;31m%s\033[0m\n' "$*" >&2; exit 1; }

command -v envsubst >/dev/null 2>&1 || die "envsubst est requis (paquet gettext)."

# ---------------------------------------------------------------- env d'entrée
#
# DOMAIN (et les éventuels secrets) peuvent venir de l'environnement, comme le
# fait Coolify quand on renseigne les variables dans l'interface.
DOMAIN_FROM_ENV="${DOMAIN:-}"

if [ ! -f "$ENV_FILE" ]; then
  umask 077
  cat > "$ENV_FILE" <<'EOF'
# Configuration de déploiement StartKit sur Coolify.
# Ne pas committer ce fichier (il contient tous les secrets de l'instance).
#
# Domaine public, SANS https:// ni slash final.
#   DOMAIN=example.com  ->  portail https://startkit.example.com
#                           Docs https://docs.example.com, Visio https://visio.example.com, etc.
# Les autres variables sont generees automatiquement si elles sont vides.
DOMAIN=
EOF
  chmod 600 "$ENV_FILE"
  cyan "→ coolify/$ENV_FILE créé : renseigne DOMAIN puis relance."
fi

# shellcheck disable=SC1090
set -a; . "./$ENV_FILE"; set +a

DOMAIN="${DOMAIN:-$DOMAIN_FROM_ENV}"
[ -n "${DOMAIN:-}" ] || die "DOMAIN est vide dans coolify/$ENV_FILE (exemple : DOMAIN=example.com)."
if ! grep -qx "DOMAIN=$DOMAIN" "$ENV_FILE"; then
  if grep -q '^DOMAIN=' "$ENV_FILE"; then
    sed -i "s|^DOMAIN=.*|DOMAIN=$DOMAIN|" "$ENV_FILE"
  else
    printf 'DOMAIN=%s\n' "$DOMAIN" >> "$ENV_FILE"
  fi
  export DOMAIN
fi

case "$DOMAIN" in
  *://*|*/*) die "DOMAIN ne doit contenir ni schéma ni slash (exemple : DOMAIN=example.com)." ;;
  *.localhost) die "DOMAIN ne peut pas être un domaine .localhost pour un déploiement distant." ;;
esac

# ------------------------------------------------------- variables à générer
# Toutes les variables référencées par les gabarits, plus celles des fichiers
# d'environnement de l'infrastructure.
mapfile -t VARS < <(
  {
    grep -rhoE '\$\{[A-Z0-9_]+\}' templates/ | sed -E 's/^\$\{|\}$//g'
    printf '%s\n' POSTGRES_SUPERUSER_PASSWORD KEYCLOAK_ADMIN_PASSWORD
  } | sort -u
)

gen() { openssl rand -hex 24; }

# Identifiant S3 non secret, fixé pour rester lisible.
if [ -z "${S3_ACCESS_KEY:-}" ]; then
  printf 'S3_ACCESS_KEY=startkit\n' >> "$ENV_FILE"
  export S3_ACCESS_KEY=startkit
fi

added=0
for v in "${VARS[@]}"; do
  current="${!v:-}"
  if [ -z "$current" ]; then
    value=$(gen)
    printf '%s=%s\n' "$v" "$value" >> "$ENV_FILE"
    export "$v=$value"
    added=$((added + 1))
  fi
done

# ------------------------------------------------------------ garde-fou local
for f in "$ROOT"/stack/env/*.env; do
  [ -f "$f" ] || continue
  if grep -q '\.localhost' "$f" && [ "$FORCE" -ne 1 ]; then
    die "$(basename "$f") ressemble à la configuration locale (domaines .localhost).
    prepare.sh l'écraserait. Relance avec --force si c'est bien ce que tu veux."
  fi
done

# ------------------------------------------------------------------- rendu
mkdir -p generated
umask 077

render() { # render <gabarit> <sortie>
  envsubst "$(printf '$%s ' "${VARS[@]}")" < "$1" > "$2"
  chmod 600 "$2"
}

for tpl in templates/env/*.env; do
  name=$(basename "$tpl")
  render "$tpl" "$ROOT/stack/env/$name"
done

render templates/startkit-realm.json generated/startkit-realm.json
render templates/livekit.yaml        generated/livekit.yaml
render templates/init.sql            generated/init.sql

# Fichiers d'environnement de l'infrastructure
write_env() { # write_env <fichier> <lignes...>
  local out="generated/$1"; shift
  : > "$out"; chmod 600 "$out"
  printf '%s\n' "$@" >> "$out"
}
write_env proxy.env    "DOMAIN=$DOMAIN"
write_env infra.env    "POSTGRES_PASSWORD=$POSTGRES_SUPERUSER_PASSWORD"
write_env s3.env       "MINIO_ROOT_USER=$S3_ACCESS_KEY" "MINIO_ROOT_PASSWORD=$S3_SECRET_KEY"
write_env keycloak.env \
  "KC_DB_PASSWORD=$DB_PASSWORD_KEYCLOAK" \
  "KC_BOOTSTRAP_ADMIN_USERNAME=admin" \
  "KC_BOOTSTRAP_ADMIN_PASSWORD=$KEYCLOAK_ADMIN_PASSWORD" \
  "KC_HOSTNAME=https://auth.$DOMAIN"

chmod 600 "$ENV_FILE"

# ----------------------------------------------------------------- contrôle
leftover=$(grep -rl '\.localhost' "$ROOT"/stack/env/*.env 2>/dev/null || true)
[ -z "$leftover" ] || warn "Attention : domaines .localhost restants dans : $leftover"

# ---------------------------------------------------------------- récapitulatif
cyan ""
cyan "StartKit — configuration de déploiement prête (domaine $DOMAIN)"
cyan ""
cat <<EOF
Portail        https://startkit.$DOMAIN
Docs           https://docs.$DOMAIN
Visio          https://visio.$DOMAIN
Messages       https://messages.$DOMAIN
Projets        https://projects.$DOMAIN
Fichiers       https://fichiers.$DOMAIN
Grist          https://grist.$DOMAIN
Transfers      https://transfers.$DOMAIN
Assistant      https://assistant.$DOMAIN
Authentification (Keycloak)  https://auth.$DOMAIN
Courrier de test (mailpit)   https://mail.$DOMAIN
Console S3                   https://s3-console.$DOMAIN

Comptes de démonstration
  user1  ${DEMO_PASSWORD_USER1}   (Camille Martin, admin Grist + Projets)
  user2  ${DEMO_PASSWORD_USER2}
  user3  ${DEMO_PASSWORD_USER3}
Comptes administrateurs
  admin@startkit.$DOMAIN (Django /admin de Docs, Fichiers, Assistant)
         mot de passe : ${DJANGO_ADMIN_PASSWORD}
  admin (console Keycloak https://auth.$DOMAIN/admin)
         mot de passe : ${KEYCLOAK_ADMIN_PASSWORD}
EOF
[ "$added" -gt 0 ] && cyan "" && cyan "$added secret(s) généré(s) et enregistré(s) dans coolify/$ENV_FILE."
cyan ""
cyan "Fichiers écrits : stack/env/ (10), coolify/generated/ (7)."
cyan "Étape suivante : voir coolify/README.md (domaines Coolify + pare-feu)."
