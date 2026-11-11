# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace layout

This directory is **not** a git repo — it groups three independent pieces used to run Tchap (French public-sector Matrix messenger) locally:

- `tchap-web-v4/` — the Tchap web client (git: `tchapgouv/tchap-web-v4`). A soft fork of Element Web; **this is where almost all development happens.**
- `tchap-local-stack/` — docker-compose backend for local dev (Synapse + MAS + Dex + Postgres). Not a git repo.
- `synapse-tchap/` — old (Dec 2022) Tchap fork of Synapse (git: `tchapgouv/synapse-tchap`). **Not used by the local stack**, which runs the upstream `matrixdotorg/synapse:latest` image. Reference only.

Run git commands inside the sub-repo (`git -C tchap-web-v4 ...`), not here.

## Local backend (`tchap-local-stack/`)

```bash
./tchap-local-stack/start.sh        # docker compose up -d
```

- Synapse `http://localhost:8008` (server_name `localhost`, SQLite). Its config/data live **outside** this folder, in `../synapse-data/` (`homeserver.yaml`), mounted at `/data`. Auth is delegated to MAS (`matrix_authentication_service` block).
- MAS `http://localhost:8084` (config `mas/config.yaml`, Postgres on host port 5434). Uses Dex as upstream OIDC provider. Image must be `ghcr.io/element-hq/matrix-authentication-service` — the old `ghcr.io/matrix-org/...:latest` tag is frozen at 0.11 and recent Synapse can't introspect its tokens. Local MAS accounts are created with `docker exec mas-local mas-cli -c /config.yaml manage register-user ...` (an `alice` account exists, email `alice@tchap.localhost`).
- Dex `http://localhost:5556/dex` — mock IdP, in-memory, single static user `test@tchap.localhost` / `password` (note: `start.sh` prints `test@localhost`, which is outdated; the Dex config is authoritative).
- Synapse and MAS use `network_mode: host`.
- The `web` service runs the front in dev mode (`node:24`, `pnpm install && pnpm start`, port 8088) on the bind-mounted `tchap-web-v4` repo. It runs as UID 1000 with the repo, pnpm store (`~/.local/share/pnpm/store`) and pnpm cache (`~/.cache/pnpm`) mounted at their host paths, so `node_modules` is shared with the host. The cache mount matters: from inside containers, concurrent connections to registry.npmjs.org time out on this machine, so the install relies on `--prefer-offline`. Logs: `docker compose logs -f web`.

## Web client (`tchap-web-v4/`)

pnpm + nx monorepo (Node 24, pnpm 11). Main app is `apps/web`; also `packages/` (module-api, shared-components, …) and `modules/` (Element modules: banner, restricted-guests, widget-*).

```bash
cd tchap-web-v4/apps/web
pnpm install            # postinstall runs scripts/tchap/apply_patches.sh (patch-package)
pnpm start              # webpack-dev-server on http://localhost:8088
pnpm build
```

`apps/web/config.json` is currently pointed at the local stack (homeserver `localhost:8008`, OIDC static client for MAS at `localhost:8084`). Other environments: `config.dev.json`, `config.preprod.json`, `config.prod.json`.

### Tests and lint

Tchap only tests what it modified — run the Tchap-scoped suites, not the full Element suite:

```bash
pnpm test:tchap                                   # jest, test/unit-tests/tchap/
pnpm exec jest test/unit-tests/tchap/<file>       # single jest test (workspace packages must be built once; test:tchap does that via nx)
pnpm test:vitest:tchap                            # vitest, only *.tchap.test.* files under src/
pnpm lint:types                                   # tsc over app, module_system, browser-test, playwright
pnpm i18n-tchap                                   # check Tchap translations
```

Repo root: `pnpm lint` (types + oxfmt + oxlint + stylelint + knip), `pnpm lint:fmt:fix`, `pnpm lint:js:fix`.

When modifying an Element component that has a test, copy the existing test into the tchap test folder (or as `*.tchap.test.*` next to the vitest one) and adapt it there.

### Fork conventions (important)

- Tchap-specific code lives in `apps/web/src/tchap/`, CSS in `apps/web/res/css/tchap/`, themes in `apps/web/res/themes/tchap-*`, tests in `apps/web/test/unit-tests/tchap/`. Prefer putting new code there.
- Any change to upstream Element code (anything outside tchap folders) must be wrapped:
  ```
  // :TCHAP: name-of-the-patch
  ...code
  // end :TCHAP:
  ```
  and registered in `apps/web/patches_tchap/tchap-modifications.json` (patch name → issue/PR + list of files).
- Dependency patches, two systems:
  1. pnpm patches (`patches/`, declared in `pnpm-workspace.yaml`) — mostly inherited from Element; `@vector-im/compound-web` is patched this way. Compound design tokens use a Tchap fork via pnpm overrides.
  2. patch-package patches in `apps/web/patches_tchap/<name>/` (one dir per patch, listed in `patches.json`) — used so several patches can target the same package (e.g. matrix-js-sdk). Create/regenerate with `pnpm patch-make <name>`; never hand-edit `.patch` files — resolve conflicts in source and regenerate (see `patches_tchap/README.md`, `scripts/tchap/merge-patches.sh`).
- Homeserver-gated features are enabled via `tchap_features` in config.json (see `tchap-web-v4/README.md` for the list).
- Code style: see `tchap-web-v4/code_style.md`.

### Local-only uncommitted patch

`apps/web/src/tchap/util/TchapUtils.ts` (`fetchHomeserverForEmail`) has a `TEMP DEV PATCH - DO NOT COMMIT` that routes `@tchap.localhost` emails to the local Synapse. Keep it out of commits.
