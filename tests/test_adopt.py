#!/usr/bin/env python3

from __future__ import annotations

import json
import os
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

    def tool(self, name: str, *args: str, env: dict[str, str] | None = None) -> int:
        return subprocess.run([sys.executable, "-B", str(self.repo / "tools" / "governance" / name), *args],
                              cwd=self.repo, capture_output=True, check=False, env=env).returncode

    @unittest.skipIf(os.name == "nt", "builds a PATH of symlinks")
    def test_proofs_run_on_a_machine_with_no_command_named_python(self) -> None:
        self.adopt()
        bin_dir = self.repo.parent / (self.repo.name + "-bin")
        bin_dir.mkdir()
        self.addCleanup(shutil.rmtree, bin_dir, True)
        (bin_dir / "git").symlink_to(shutil.which("git"))
        env = {**os.environ, "PATH": str(bin_dir)}
        self.assertEqual(self.tool("rulectl", "check", "--repo", ".", "--prove", env=env), 0)

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

    def test_file_length_rule_is_installed_and_proven(self) -> None:
        self.adopt()
        self.assertEqual(self.tool("rulekit", "check", "--rule", "R-002", ".governance/bad/R-002.ts"), 3)
        (self.repo / "src" / "huge.ts").write_text("export const a = 1;\n" * 401, encoding="utf-8")
        self.assertEqual(self.tool("rulekit", "check"), 3)

    def test_python_project_gets_the_strict_linter_and_type_checker(self) -> None:
        (self.repo / "src" / "app.ts").unlink()
        (self.repo / "src" / "app.py").write_text("def total(prices):\n    return sum(prices)\n", encoding="utf-8")
        out = self.adopt()
        rules = json.loads((self.repo / ".governance/rules.json").read_text())["rules"]
        self.assertEqual([rule["argv"][0] for rule in rules if rule["kind"] == "linter"], ["ruff", "mypy"])
        self.assertIn("select", (self.repo / "ruff.toml").read_text())
        self.assertIn("pip install ruff mypy", (self.repo / ".github/workflows/governance.yml").read_text())
        self.assertIn("R-004", (self.repo / "AGENTS.md").read_text())
        if shutil.which("ruff") and shutil.which("mypy"):
            self.assertEqual(self.tool("rulekit", "check"), 0)
            self.assertEqual(self.tool("rulectl", "check", "--repo", ".", "--prove"), 0)
            (self.repo / "src" / "new.py").write_text("def more(x):\n    return x\n", encoding="utf-8")
            self.assertEqual(self.tool("rulekit", "check"), 3)
        else:
            self.assertIn("NOT DONE", out)
            self.assertEqual(self.tool("rulekit", "check"), 127)

    def test_node_project_gets_eslint_and_the_strict_type_check(self) -> None:
        (self.repo / "package.json").write_text("{}", encoding="utf-8")
        (self.repo / "tsconfig.json").write_text("{}", encoding="utf-8")
        self.assertIn("NOT DONE", self.adopt())
        rules = json.loads((self.repo / ".governance/rules.json").read_text())["rules"]
        self.assertEqual([rule["argv"][2] for rule in rules if rule["kind"] == "linter"], ["tsc", "eslint"])
        self.assertIn("strict", (self.repo / "eslint.config.mjs").read_text())
        self.assertIn("npm ci", (self.repo / ".github/workflows/governance.yml").read_text())


if __name__ == "__main__":
    unittest.main()
