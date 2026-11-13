#!/usr/bin/env python3
"""Génère coolify/compose.flat.yml, le compose réellement déployé par Coolify.

Pourquoi ce fichier existe
--------------------------
Coolify ne lit qu'UN seul fichier Compose (celui déclaré dans « Docker Compose
Location », lu depuis Git) et ne résout pas la clé `include:` : son parseur ne
connaît que `services`, `volumes`, `networks`, `configs` et `secrets`, puis il
réécrit ce fichier dans le répertoire de déploiement avant de lancer
`docker compose`. Un fichier qui utilise `include:` est donc silencieusement
vidé de ses services inclus (seul le bloc `services:` du fichier d'entrée
survit), d'où l'erreur « service … has neither an image nor a build context ».

Ce script produit donc un fichier autonome, sans `include:`, qui est commité
(Coolify lit le fichier depuis Git, pas depuis le répertoire de déploiement).

Ce qu'il fait en plus de résoudre les `include:`
------------------------------------------------
- Réécrit les chemins relatifs (`volumes`, `env_file`, `configs`, `secrets`)
  par rapport à la racine du dépôt, puisque la ressource Coolify utilise
  « Base Directory = / ».
- Remplace chaque `env_file:` par des `environment:` qui référencent des
  variables Coolify préfixées (`${MEET_DB_NAME?}`) : Coolify remplace les
  `env_file:` des services par un unique `.env` commun à toute la ressource,
  or les fichiers d'environnement de StartKit partagent des clés (`DB_NAME`,
  `DJANGO_SECRET_KEY`, …) avec des valeurs différentes selon l'application.
  Les valeurs sont à coller dans Coolify (voir coolify/README.md §4) ;
  `coolify/prepare.sh` produit le bloc prêt à coller.

Usage :
    python3 coolify/flatten.py            # régénère coolify/compose.flat.yml
    python3 coolify/flatten.py --check    # échoue si le fichier est périmé
"""

from __future__ import annotations

import argparse
import copy
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "coolify" / "compose.yml"
OUTPUT = ROOT / "coolify" / "compose.flat.yml"

# Répertoires des gabarits qui font foi pour les clés de chaque fichier d'env.
# stack/env/<app>.env        <- coolify/templates/env/<app>.env
# coolify/generated/<f>.env  <- coolify/templates/infra-env/<f>.env
ENV_TEMPLATE_DIRS = {
    "stack/env": ROOT / "coolify" / "templates" / "env",
    "coolify/generated": ROOT / "coolify" / "templates" / "infra-env",
}

KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")

HEADER = """\
# ATTENTION : fichier généré par `python3 coolify/flatten.py`, ne pas éditer.
#
# Source : coolify/compose.yml (+ les fichiers qu'il inclut).
# Cible  : ressource Coolify « Docker Compose »
#            Base Directory ............ /
#            Docker Compose Location ... /coolify/compose.flat.yml
#
# Coolify ne résout pas `include:` et remplace les `env_file:` des services par
# un `.env` commun : ce fichier est donc aplati et les `env_file:` y sont
# convertis en `environment:` référençant les variables Coolify prefixées
# (${MEET_DB_NAME?}, …). Le bloc de valeurs à coller dans Coolify est produit
# par `bash coolify/prepare.sh` : coolify/generated/variables-coolify.env.
"""


def rel(path: Path) -> str:
    """Chemin lisible dans les messages d'erreur."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fail(message: str) -> "NoReturn":  # type: ignore[name-defined]
    raise SystemExit(f"flatten.py: {message}")


def load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        fail(f"{rel(path)} est introuvable.")
    except yaml.YAMLError as exc:
        fail(f"{rel(path)} n'est pas un YAML valide : {exc}")
    if not isinstance(data, dict):
        fail(f"{rel(path)} : la racine doit être une table YAML.")
    return data


def rebase(path: str, file_dir: Path) -> str:
    """Exprime un chemin relatif à partir de la racine du dépôt (Base Directory)."""
    if not path.startswith(("./", "../")):
        return path
    absolute = os.path.normpath(os.path.join(file_dir, path))
    relative = Path(os.path.relpath(absolute, ROOT)).as_posix()
    return relative if relative.startswith("../") else f"./{relative}"


def rebase_short_volume(volume: str, file_dir: Path) -> str:
    """Réécrit la source d'un volume en syntaxe courte (`source:target[:mode]`)."""
    source, sep, rest = volume.partition(":")
    if not sep:
        return volume
    return f"{rebase(source, file_dir)}:{rest}"


def ns_of(env_path: Path) -> str:
    """Préfixe des variables Coolify : meet.env -> MEET_, docs-yhub.env -> DOCS_YHUB_."""
    stem = env_path.name[: -len(".env")] if env_path.name.endswith(".env") else env_path.stem
    return stem.upper().replace("-", "_").replace(".", "_") + "_"


def template_for(env_path: Path) -> Path:
    """Gabarit qui fait foi pour les clés du fichier d'environnement."""
    try:
        relative = env_path.relative_to(ROOT)
    except ValueError:
        fail(f"{env_path} est hors du dépôt : les env_file doivent vivre dans stack/env/ ou coolify/generated/.")
    # Les deux premiers segments sont typiquement ("stack", "env") ou ("coolify", "generated").
    for prefix, directory in ENV_TEMPLATE_DIRS.items():
        if str(Path(*relative.parts[:2])).replace(os.sep, "/") == prefix:
            template = directory / env_path.name
            if not template.is_file():
                fail(
                    f"{rel(env_path)} n'a pas de gabarit de clés ({rel(template)}).\n"
                    "  Ajoute-le : c'est lui qui liste les variables exposées à Coolify."
                )
            return template
    fail(f"{rel(env_path)} doit être dans stack/env/ ou coolify/generated/.")
    raise AssertionError


def env_keys(env_path: Path) -> list[str]:
    """Clés déclarées dans le gabarit, dans l'ordre du fichier (sans doublon)."""
    keys: list[str] = []
    for line in template_for(env_path).read_text(encoding="utf-8").splitlines():
        match = KEY_RE.match(line)
        if match and match.group(1) not in keys:
            keys.append(match.group(1))
    if not keys:
        fail(f"{rel(template_for(env_path))} ne déclare aucune clé KEY=VALUE.")
    return keys


def as_env_paths(value) -> list:
    """`env_file` accepte une chaîne, une liste de chaînes ou des objets {path: …}."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        fail(f"env_file inattendu : {value!r}")
    paths = []
    for item in value:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, dict) and isinstance(item.get("path"), str):
            paths.append(item["path"])
        else:
            fail(f"env_file inattendu : {item!r}")
    return paths


def normalize_env(value) -> dict:
    """Normalise `environment:` (liste ou table) en dictionnaire."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    environment: dict = {}
    for item in value:
        if isinstance(item, str):
            key, sep, val = item.partition("=")
            environment[key] = val if sep else None
        elif isinstance(item, dict):
            environment.update(item)
        else:
            fail(f"environment inattendu : {item!r}")
    return environment


def transform_service(name: str, service: dict, file_dir: Path, used: list[Path]) -> dict:
    service = copy.deepcopy(service)

    volumes = service.get("volumes")
    if isinstance(volumes, list):
        rewritten = []
        for volume in volumes:
            if isinstance(volume, str):
                rewritten.append(rebase_short_volume(volume, file_dir))
            elif isinstance(volume, dict) and isinstance(volume.get("source"), str):
                volume = dict(volume)
                volume["source"] = rebase(volume["source"], file_dir)
                rewritten.append(volume)
            else:
                rewritten.append(volume)
        service["volumes"] = rewritten

    env_files = service.pop("env_file", None)
    references: dict[str, str] = {}
    for path in as_env_paths(env_files):
        env_path = Path(os.path.normpath(os.path.join(file_dir, path)))
        used.append(env_path)
        prefix = ns_of(env_path)
        for key in env_keys(env_path):
            # `${VAR?}` (sans `:`) : la variable doit exister dans Coolify, mais
            # une valeur vide reste légitime (`SUPPORT_URL=`, `OIDC_STORE_CLAIMS=`…).
            # Avec `:?`, Compose refuserait ces variables volontairement vides.
            references[key] = "${%s%s?}" % (prefix, key)

    if references:
        # `environment:` prime sur `env_file:` en Compose : l'explicite passe en dernier.
        service["environment"] = {**references, **normalize_env(service.get("environment"))}

    return service


def transform(data: dict, file_dir: Path, used: list[Path]) -> dict:
    data = copy.deepcopy(data)
    services = data.pop("services", None)
    # Les blocs `x-…` ne servent qu'aux ancres YAML, déjà résolues au chargement.
    out = {key: value for key, value in data.items() if not key.startswith("x-")}

    for section in ("configs", "secrets"):
        for declaration in (out.get(section) or {}).values():
            if isinstance(declaration, dict) and isinstance(declaration.get("file"), str):
                declaration["file"] = rebase(declaration["file"], file_dir)

    if services is not None:
        if not isinstance(services, dict):
            fail(f"{rel(file_dir)} : `services` doit être une table YAML.")
        out["services"] = {
            name: transform_service(name, service or {}, file_dir, used)
            for name, service in services.items()
        }
    return out


def deep_merge(base, override):
    """Fusion Compose : les tables fusionnent, tout le reste est remplacé par le fichier appelant."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = deep_merge(merged[key], value) if key in merged else copy.deepcopy(value)
        return merged
    return copy.deepcopy(override)


def resolve(path: Path, seen: tuple[Path, ...], used: list[Path]) -> dict:
    if path in seen:
        cycle = " -> ".join(rel(entry) for entry in (*seen, path))
        fail(f"include circulaire : {cycle}")
    data = load_yaml(path)
    includes = data.pop("include", None) or []
    if isinstance(includes, (str, dict)):
        includes = [includes]

    merged: dict = {}
    for include in includes:
        if isinstance(include, str):
            included_path = include
        elif isinstance(include, dict) and isinstance(include.get("path"), str):
            if include.get("env_file") or include.get("project_directory"):
                fail(f"{rel(path)} : les options `env_file`/`project_directory` de `include` ne sont pas gérées.")
            included_path = include["path"]
        else:
            fail(f"{rel(path)} : entrée `include` inattendue : {include!r}")
        target = Path(os.path.normpath(os.path.join(path.parent, included_path)))
        merged = deep_merge(merged, resolve(target, (*seen, path), used))

    return deep_merge(merged, transform(data, path.parent, used))


def render(flat: dict) -> str:
    """Ordonne les sections comme Compose et produit le YAML final."""
    order = ["name", "services", "volumes", "networks", "configs", "secrets"]
    ordered = {key: flat[key] for key in order if key in flat}
    for key, value in flat.items():
        if key not in ordered:
            ordered[key] = value
    body = yaml.dump(ordered, sort_keys=False, default_flow_style=False, allow_unicode=True, width=200)
    return HEADER + "\n" + body


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère coolify/compose.flat.yml.")
    parser.add_argument("--check", action="store_true", help="échoue si le fichier généré est périmé")
    args = parser.parse_args()

    used: list[Path] = []
    flat = resolve(ENTRY, (), used)
    text = render(flat)

    if args.check:
        if not OUTPUT.is_file():
            print(f"flatten.py: {rel(OUTPUT)} est absent — lance `python3 coolify/flatten.py`.", file=sys.stderr)
            return 1
        if OUTPUT.read_text(encoding="utf-8") != text:
            print(
                f"flatten.py: {rel(OUTPUT)} est périmé — lance `python3 coolify/flatten.py`.",
                file=sys.stderr,
            )
            return 1
        print(f"flatten.py: {rel(OUTPUT)} est à jour.")
        return 0

    OUTPUT.write_text(text, encoding="utf-8")
    services = flat.get("services", {})
    env_files = sorted({rel(path) for path in used})
    variables = len({(ns_of(p), k) for p in used for k in env_keys(p)})
    print(f"flatten.py: {rel(OUTPUT)} généré — {len(services)} services, "
          f"{len(env_files)} fichiers d'env, {variables} variables Coolify.")
    if env_files:
        print("  env_file -> environment : " + ", ".join(env_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
