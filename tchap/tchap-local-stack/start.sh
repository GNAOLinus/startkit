#!/usr/bin/env bash
# Lance tout le backend Tchap local (Synapse + MAS + Dex + Postgres) + le front web en une commande.
set -euo pipefail
cd "$(dirname "$0")"
docker compose up -d
echo
echo "Stack prête :"
echo "  Synapse : http://localhost:8008"
echo "  MAS     : http://localhost:8084"
echo "  Dex     : http://localhost:5556/dex"
echo "  Front   : http://localhost:8088  (1er démarrage long : pnpm install + compilation, suivre avec: docker compose logs -f web)"
echo
echo "Connexion dans le front Tchap (http://localhost:8088) : email test@tchap.localhost / mot de passe password"
echo "Compte MAS local (formulaire identifiant/mot de passe de MAS) : alice / même mot de passe"
