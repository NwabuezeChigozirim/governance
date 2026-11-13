#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
INSTALL = PACKAGE / "scripts" / "install.py"


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        self.target = self.home / "plugins" / "local" / "trust"

    def install(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(INSTALL), "--target", str(self.target)],
                              capture_output=True, text=True, check=False)

    def test_install_copies_the_plugin_and_pins_the_hook_interpreter(self) -> None:
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in (".cursor-plugin/plugin.json", "skills/govern/SKILL.md", "skills/grilling/SKILL.md", "skills/start/STEPS.md",
                     "scripts/stagectl", "scripts/where", "hooks/guard.py", "LICENSE", "THIRD_PARTY_LICENSE-mattpocock-skills"):
            self.assertTrue((self.target / name).is_file(), name)
        self.assertFalse((self.target / "tests").exists())
        hooks = json.loads((self.target / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        commands = [entry["command"] for entries in hooks["hooks"].values() for entry in entries]
        self.assertTrue(commands)
        for command in commands:
            self.assertFalse(command.startswith("python3 "), command)
            self.assertIn(Path(sys.executable).as_posix(), command)
            self.assertIn("${CURSOR_PLUGIN_ROOT}/hooks/guard.py", command)
        source = json.loads((PACKAGE / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertTrue(all(e["command"].startswith("python3 ") for es in source["hooks"].values() for e in es))

    def test_reinstall_replaces_a_previous_install(self) -> None:
        self.install()
        (self.target / "stale.txt").write_text("old", encoding="utf-8")
        self.assertEqual(self.install().returncode, 0)
        self.assertFalse((self.target / "stale.txt").exists())

    def old_install(self, name: str) -> Path:
        old = self.target.parent / name
        (old / ".cursor-plugin").mkdir(parents=True)
        (old / ".cursor-plugin" / "plugin.json").write_text(json.dumps({"name": name}), encoding="utf-8")
        return old

    def test_install_removes_the_two_plugins_it_replaces(self) -> None:
        governance, intent = self.old_install("governance"), self.old_install("intent")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(governance.exists())
        self.assertFalse(intent.exists())
        self.assertIn("removed:", result.stdout)
        self.assertEqual(json.loads((self.target / ".cursor-plugin" / "plugin.json").read_text())["name"], "trust")

    def test_install_leaves_an_unrelated_directory_with_an_old_name_alone(self) -> None:
        other = self.target.parent / "intent"
        other.mkdir(parents=True)
        (other / "notes.txt").write_text("mine", encoding="utf-8")
        self.assertEqual(self.install().returncode, 0)
        self.assertTrue((other / "notes.txt").is_file())

    def test_install_refuses_to_replace_an_unrelated_directory(self) -> None:
        self.target.mkdir(parents=True)
        (self.target / "notes.txt").write_text("mine", encoding="utf-8")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.target / "notes.txt").is_file())


if __name__ == "__main__":
    unittest.main()
