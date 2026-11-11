#!/usr/bin/env bash
# Crée un compte StartKit (Keycloak, royaume « startkit ») utilisable dans
# Docs, Visio, Fichiers, Grist, Transfers, Messages et Projets.
#
#   ./nouveau-compte.sh <identifiant> <prénom> <nom> [mot de passe]
#
# Exemple : ./nouveau-compte.sh alice Alice Durand
#   -> e-mail alice@startkit.localhost, mot de passe « alice » (par défaut = identifiant)
set -euo pipefail
cd "$(dirname "$0")"

if [ $# -lt 3 ]; then
  echo "Usage : $0 <identifiant> <prénom> <nom> [mot de passe]" >&2
  exit 1
fi

login="$1"; first="$2"; last="$3"; password="${4:-$1}"
email="${login}@startkit.localhost"

kc() { docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh "$@"; }

kc config credentials --server http://localhost:8080 --realm master --user admin --password admin >/dev/null 2>&1
kc create users -r startkit \
  -s username="$login" -s email="$email" -s emailVerified=true \
  -s firstName="$first" -s lastName="$last" -s enabled=true >/dev/null
kc set-password -r startkit --username "$login" --new-password "$password" >/dev/null

echo "Compte créé : $first $last"
echo "  identifiant  : $login   (ou $email)"
echo "  mot de passe : $password"
echo "  boîte Messages : $email (créée à la première connexion)"
echo "Connexion : http://startkit.localhost:8000/espace/"
