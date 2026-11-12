#!/usr/bin/env python3
"""Structural checks for the plugin package itself."""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
SKILLS = PACKAGE / "skills"
SKILL_REFERENCE = re.compile(r"\*\*([a-z][a-z0-9-]+)\*\* (?:principle )?skill")
SIBLING_LINK = re.compile(r"\]\(\.\./([a-z0-9-]+)/SKILL\.md\)")
# Skills from other plugins, the generated project skill, and Cursor built-ins.
EXTERNAL = {"create-skill", "deslop", "control-ui", "control-cli", "babysit"}


def skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS.iterdir() if p.is_dir())


class PackageTests(unittest.TestCase):
    def test_manifest_points_at_existing_components(self) -> None:
        manifest = json.loads((PACKAGE / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        for key in ("skills", "hooks", "agents"):
            self.assertTrue((PACKAGE / manifest[key]).exists(), f"{key}: {manifest[key]}")
        hooks = json.loads((PACKAGE / manifest["hooks"]).read_text(encoding="utf-8"))
        for entries in hooks["hooks"].values():
            for entry in entries:
                script = re.search(r"\$\{CURSOR_PLUGIN_ROOT\}/(\S+)", entry["command"]).group(1)
                self.assertTrue((PACKAGE / script).is_file(), script)

    def test_every_skill_has_matching_frontmatter(self) -> None:
        for directory in skill_dirs():
            text = (directory / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), directory.name)
            name = re.search(r"^name:\s*(\S+)\s*$", text.split("---", 2)[1], re.MULTILINE)
            self.assertIsNotNone(name, directory.name)
            self.assertEqual(name.group(1), directory.name)

    def test_every_referenced_skill_ships_with_the_plugin(self) -> None:
        present = {p.name for p in skill_dirs()}
        missing: dict[str, set[str]] = {}
        for path in [*SKILLS.rglob("*.md"), *(PACKAGE / "agents").glob("*.md")]:
            if "scripts/test" in path.as_posix():
                continue
            text = path.read_text(encoding="utf-8")
            for name in set(SKILL_REFERENCE.findall(text)) | set(SIBLING_LINK.findall(text)):
                resolved = name if name in present else f"principle-{name}"
                if resolved not in present and name not in EXTERNAL:
                    missing.setdefault(name, set()).add(path.relative_to(PACKAGE).as_posix())
        self.assertEqual(missing, {})

    def test_no_reference_to_the_upstream_router_remains(self) -> None:
        for path in [*SKILLS.rglob("*.md"), *(PACKAGE / "agents").glob("*.md")]:
            if "scripts/test" in path.as_posix():
                continue
            self.assertNotIn("poteto-mode", path.read_text(encoding="utf-8"), path)

    def test_scripts_named_by_skills_exist(self) -> None:
        for name in ("stagectl", "verifyctl", "rulectl"):
            self.assertTrue((PACKAGE / "scripts" / name).is_file())


if __name__ == "__main__":
    unittest.main()
