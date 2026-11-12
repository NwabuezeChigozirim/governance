#!/usr/bin/env python3
"""Install this plugin for Cursor as a local plugin.

Copies the plugin into ~/.cursor/plugins/local/governance and pins the hook commands
to the Python interpreter that ran this installer, so the hooks do not depend on a
`python3` command being on PATH (it often is not on Windows). Run it again after
pulling changes. Standard library only; Linux, macOS and Windows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parents[1]
PARTS = (".cursor-plugin", "agents", "hooks", "scripts", "skills", "README.md", "THIRD_PARTY_LICENSE-pstack")
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules", ".verify")


def install(target: Path, python: str) -> Path:
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.exists():
        marker = target / ".cursor-plugin" / "plugin.json"
        if not marker.is_file() or json.loads(marker.read_text(encoding="utf-8")).get("name") != "governance":
            raise SystemExit(f"refusing to replace {target}: it is not a previous install of this plugin")
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for name in PARTS:
        source = SOURCE / name
        if source.is_dir():
            shutil.copytree(source, target / name, ignore=SKIP)
        else:
            shutil.copy2(source, target / name)
    hooks_file = target / "hooks" / "hooks.json"
    hooks = json.loads(hooks_file.read_text(encoding="utf-8"))
    interpreter = Path(python).as_posix()
    quoted = f'"{interpreter}"' if " " in interpreter else interpreter
    for entries in hooks["hooks"].values():
        for entry in entries:
            command = entry["command"]
            if command.startswith("python3 "):
                entry["command"] = quoted + command[len("python3"):]
    hooks_file.write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", default=str(Path.home() / ".cursor" / "plugins" / "local" / "governance"),
                        help="where to install (default: Cursor's local plugin directory)")
    args = parser.parse_args()
    target = install(Path(args.target).expanduser(), sys.executable)
    print(f"installed: {target}")
    print(f"hooks run with: {sys.executable}")
    print("Restart Cursor, then start a task with /govern <what you want>.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
