#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


RULECTL = Path(__file__).resolve().parents[1] / "scripts" / "rulectl"
HEADER = "| ID | Rule | Level | Enforced by | Proof | Notes |\n|---|---|---|---|---|---|\n"
PYTHON = Path(sys.executable).as_posix()  # Forward slashes survive shlex on Windows.
FAILS = f"`{PYTHON} -c \"raise SystemExit(1)\"`"
PASSES = f"`{PYTHON} -c pass`"


class RulectlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, True)
        (self.repo / "eslint.config.js").write_text("export default [];\n", encoding="utf-8")
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "test_boundary.py").write_text("def test(): pass\n", encoding="utf-8")

    def write(self, rows: str, *, heading: str = "## Rules", header: str = HEADER) -> None:
        text = f"# Agent guide\n\nIntro.\n\n{heading}\n\n{header}{rows}\n## Commands\n\n| a | b |\n|---|---|\n| x | y |\n"
        (self.repo / "AGENTS.md").write_text(text, encoding="utf-8")

    def check(self, *extra: str) -> tuple[int, dict]:
        result = subprocess.run(
            [sys.executable, "-B", str(RULECTL), "--json", "check", "--repo", str(self.repo), *extra],
            capture_output=True, text=True, check=False,
        )
        return result.returncode, json.loads(result.stdout)

    def test_enforced_rules_pass(self) -> None:
        self.write(
            f"| R-001 | Renderer never imports main | lint | `eslint.config.js` rule no-main-import | {FAILS} | |\n"
            f"| R-002 | Totals never go negative | test | `tests/test_boundary.py::test` | {FAILS} | |\n"
        )
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertEqual(out["rules"], 2)
        self.assertEqual(out["unenforced"], [])

    def test_rule_without_existing_enforcer_fails(self) -> None:
        self.write(f"| R-001 | No raw SQL | lint | `tools/missing_lint.py` | {FAILS} | |\n")
        code, out = self.check()
        self.assertEqual(code, 3)
        self.assertTrue(any("R-001" in e and "not found" in e for e in out["errors"]))

    def test_prose_only_enforcer_fails(self) -> None:
        self.write(f"| R-001 | No raw SQL | lint | reviewers check this | {FAILS} | |\n")
        code, out = self.check()
        self.assertEqual(code, 3)
        self.assertTrue(any("cite in backticks" in e for e in out["errors"]))

    def test_enforcer_outside_repository_is_not_accepted(self) -> None:
        self.write(f"| R-001 | No raw SQL | lint | `../eslint.config.js` | {FAILS} | |\n")
        self.assertEqual(self.check()[0], 3)

    def test_docs_rule_needs_a_reason_and_is_reported_unenforced(self) -> None:
        self.write("| R-001 | Prefer small PRs | docs | | | |\n")
        code, out = self.check()
        self.assertEqual(code, 3)
        self.write("| R-001 | Prefer small PRs | docs | | | Judgment call; no size threshold fits every change |\n")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertEqual(out["unenforced"], ["R-001"])

    def test_max_docs_limits_unenforced_rules(self) -> None:
        self.write(
            "| R-001 | Prefer small PRs | docs | | | Judgment call |\n"
            "| R-002 | Name things clearly | docs | | | Judgment call |\n"
        )
        self.assertEqual(self.check("--max-docs", "2")[0], 0)
        code, out = self.check("--max-docs", "1")
        self.assertEqual(code, 3)
        self.assertTrue(any("exceed the limit" in e for e in out["errors"]))

    def test_duplicate_bad_id_and_bad_level_fail(self) -> None:
        self.write(
            f"| R-001 | A | lint | `eslint.config.js` | {FAILS} | |\n"
            f"| R-001 | B | lint | `eslint.config.js` | {FAILS} | |\n"
            f"| RULE7 | C | lint | `eslint.config.js` | {FAILS} | |\n"
            f"| R-003 | D | review | `eslint.config.js` | {FAILS} | |\n"
        )
        code, out = self.check()
        self.assertEqual(code, 3)
        joined = " ".join(out["errors"])
        self.assertIn("duplicate ID", joined)
        self.assertIn("must look like R-001", joined)
        self.assertIn("level must be one of", joined)

    def test_missing_section_wrong_columns_and_empty_table_fail(self) -> None:
        self.write("", heading="## Conventions")
        self.assertTrue(any("no '## Rules' section" in e for e in self.check()[1]["errors"]))
        self.write("| R-001 | A | lint |\n", header="| ID | Rule | Level |\n|---|---|---|\n")
        self.assertTrue(any("columns must be" in e for e in self.check()[1]["errors"]))
        self.write("")
        self.assertTrue(any("no rules" in e for e in self.check()[1]["errors"]))

    def test_tables_in_other_sections_are_ignored(self) -> None:
        self.write(f"| R-001 | A | lint | `eslint.config.js` | {FAILS} | |\n")
        self.assertEqual(self.check()[1]["rules"], 1)

    def test_enforced_rule_needs_a_proof_command(self) -> None:
        self.write("| R-001 | No raw SQL | lint | `eslint.config.js` | we tested it once | |\n")
        code, out = self.check()
        self.assertEqual(code, 3)
        self.assertTrue(any("Proof must be one backticked command" in e for e in out["errors"]))

    def test_prove_accepts_a_proof_that_fails_and_is_not_run_without_the_flag(self) -> None:
        self.write(f"| R-001 | No raw SQL | lint | `eslint.config.js` | {FAILS} | |\n")
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("proven", out)
        code, out = self.check("--prove")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["proven"], ["R-001"])

    def test_prove_rejects_an_enforcer_that_lets_the_bad_example_through(self) -> None:
        self.write(f"| R-001 | No raw SQL | lint | `eslint.config.js` | {PASSES} | |\n")
        self.assertEqual(self.check()[0], 0)
        code, out = self.check("--prove")
        self.assertEqual(code, 3)
        self.assertTrue(any("accepted the bad example" in e for e in out["errors"]))

    def test_prove_does_not_count_a_missing_tool_as_a_rejection(self) -> None:
        self.write("| R-001 | No raw SQL | lint | `eslint.config.js` | `no-such-linter-xyz bad.ts` | |\n")
        code, out = self.check("--prove")
        self.assertEqual(code, 3)
        self.assertTrue(any("not found" in e for e in out["errors"]))

    def test_missing_instruction_file_fails(self) -> None:
        self.assertEqual(self.check()[0], 3)


if __name__ == "__main__":
    unittest.main()
