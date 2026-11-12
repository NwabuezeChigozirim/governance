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
        self.target = self.home / "plugins" / "local" / "governance"

    def install(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(INSTALL), "--target", str(self.target)],
                              capture_output=True, text=True, check=False)

    def test_install_copies_the_plugin_and_pins_the_hook_interpreter(self) -> None:
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in (".cursor-plugin/plugin.json", "skills/govern/SKILL.md", "scripts/stagectl", "hooks/guard.py"):
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

    def test_install_refuses_to_replace_an_unrelated_directory(self) -> None:
        self.target.mkdir(parents=True)
        (self.target / "notes.txt").write_text("mine", encoding="utf-8")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.target / "notes.txt").is_file())


if __name__ == "__main__":
    unittest.main()
