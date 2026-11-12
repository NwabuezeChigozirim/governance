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
ADOPT = PACKAGE / "scripts" / "adopt.py"


class AdoptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.ts").write_text("// legacy note\nexport const a = 1;\n", encoding="utf-8")
        (self.repo / "AGENTS.md").write_text("# Agent guide\n\nBe careful.\n", encoding="utf-8")

    def adopt(self) -> str:
        result = subprocess.run([sys.executable, "-B", str(ADOPT), "--repo", str(self.repo)], capture_output=True,
                                text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def tool(self, name: str, *args: str) -> int:
        return subprocess.run([sys.executable, "-B", str(self.repo / "tools" / "governance" / name), *args],
                              cwd=self.repo, capture_output=True, check=False).returncode

    def test_adopted_project_passes_its_own_rules_and_proves_them(self) -> None:
        self.adopt()
        self.assertTrue((self.repo / ".governance" / "bad" / "R-001.ts").is_file())
        self.assertEqual(self.tool("rulekit", "check"), 0)
        self.assertEqual(self.tool("rulectl", "check", "--repo", ".", "--prove"), 0)
        self.assertTrue(json.loads((self.repo / ".governance/config.json").read_text())["require_stage"])
        self.assertIn(".verify/", (self.repo / ".gitignore").read_text().splitlines())
        self.assertIn("stagectl gate", (self.repo / ".github/workflows/governance.yml").read_text())

    def test_existing_comment_is_tolerated_and_a_new_one_fails(self) -> None:
        self.adopt()
        (self.repo / "src" / "new.ts").write_text("// excuse\nexport const b = 2;\n", encoding="utf-8")
        self.assertEqual(self.tool("rulekit", "check"), 3)

    def test_running_again_keeps_the_owner_s_changes(self) -> None:
        self.adopt()
        config = self.repo / ".governance" / "config.json"
        config.write_text(json.dumps({"version": 1, "require_stage": False, "exempt": ["docs/**"]}), encoding="utf-8")
        guide = (self.repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("kept", self.adopt())
        self.assertFalse(json.loads(config.read_text())["require_stage"])
        self.assertEqual((self.repo / "AGENTS.md").read_text(encoding="utf-8"), guide)
        self.assertEqual(guide.count("## Rules"), 1)
        self.assertIn("Be careful.", guide)


if __name__ == "__main__":
    unittest.main()
