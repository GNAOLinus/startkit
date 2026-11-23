import json
import os
import re
from pathlib import Path


ROOT = Path("/templates")
OUTPUTS = {
    "init.sql": Path("/postgres-init/init.sql"),
    "startkit-realm.json": Path("/keycloak-import/startkit-realm.json"),
    "livekit.yaml": Path("/livekit-config/livekit.yaml"),
}
PLACEHOLDER = re.compile(r"\$\{([A-Z0-9_]+)\}")


def render(source: Path, destination: Path) -> None:
    content = source.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in os.environ:
            raise RuntimeError(f"Missing environment variable required by {source.name}: {key}")
        return os.environ[key]

    rendered = PLACEHOLDER.sub(replace, content)
    if PLACEHOLDER.search(rendered):
        raise RuntimeError(f"Unresolved template placeholder in {source.name}")
    destination.write_text(rendered, encoding="utf-8")
    destination.chmod(0o644)


def main() -> None:
    for source_name, destination in OUTPUTS.items():
        render(ROOT / source_name, destination)

    json.loads(OUTPUTS["startkit-realm.json"].read_text(encoding="utf-8"))
    print("StartKit runtime configuration rendered.")


if __name__ == "__main__":
    main()
