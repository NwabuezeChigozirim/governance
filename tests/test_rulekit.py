#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RULEKIT = Path(__file__).resolve().parents[1] / "scripts" / "rulekit"
MESSAGE = "Do the right thing instead of this."


class RulekitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def write(self, name: str, text: str) -> None:
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def rules(self, *rules: dict, exclude: list[str] | None = None) -> None:
        self.write(".governance/rules.json", json.dumps({"version": 1, "exclude": exclude or [], "rules": [
            {"message": MESSAGE, **rule} for rule in rules]}))

    def kit(self, *args: str) -> tuple[int, dict]:
        result = subprocess.run([sys.executable, "-B", str(RULEKIT), "--repo", str(self.repo), "--json", *args],
                                capture_output=True, text=True, check=False)
        return result.returncode, json.loads(result.stdout)

    def lines(self, *args: str) -> list[tuple[str, int]]:
        return [(item["path"], item["line"]) for item in self.kit("check", *args)[1]["violations"]]

    def test_python_comments_are_found_but_strings_and_shebang_are_not(self) -> None:
        self.rules({"id": "R-001", "kind": "ban-comments", "include": ["**/*.py"]})
        self.write("a.py", '#!/usr/bin/env python3\nURL = "http://x/#frag"  # why\n"""Doc # not a comment."""\n')
        self.assertEqual(self.lines(), [("a.py", 2)])

    def test_c_style_comments_skip_strings_templates_and_regex_literals(self) -> None:
        self.rules({"id": "R-001", "kind": "ban-comments", "include": ["**/*.ts"]})
        self.write("a.ts", "const a = 'http://x';\nconst b = `// ${a} /* no */`;\nconst c = /https?:\\/\\//.test(a);\n"
                           "const d = 4 / 2; // real\n/* block\n   spans */\nconst e = 1;\n")
        self.assertEqual(self.lines(), [("a.ts", 4), ("a.ts", 5)])

    def test_allow_list_keeps_tool_directives(self) -> None:
        self.rules({"id": "R-001", "kind": "ban-comments", "include": ["**/*.ts"], "allow": ["^eslint-"]})
        self.write("a.ts", "// eslint-disable-next-line no-console\nconsole.log(1);\n// because\n")
        self.assertEqual(self.lines(), [("a.ts", 3)])

    def test_import_boundary_between_directories(self) -> None:
        self.rules({"id": "R-002", "kind": "ban-import", "include": ["src/renderer/**"], "forbid": ["src/main"],
                    "forbid_specifiers": ["^electron$"]})
        self.write("src/renderer/view.ts", "import { db } from '../main/db';\nimport x from '../shared/x';\n"
                                           "const e = require('electron');\nconst m = await import('../main');\n")
        self.write("src/main/db.ts", "import fs from 'fs';\n")
        self.assertEqual(self.lines(), [("src/renderer/view.ts", 1), ("src/renderer/view.ts", 3),
                                        ("src/renderer/view.ts", 4)])

    def test_python_import_boundary_resolves_absolute_and_relative_modules(self) -> None:
        self.rules({"id": "R-002", "kind": "ban-import", "include": ["app/web/**"], "forbid": ["app/db"]})
        self.write("app/web/views.py", "from app.db import models\nfrom ..db.models import User\nimport app.core, app.db.q\n"
                                       "from app.database import x\n")
        self.assertEqual(self.lines(), [("app/web/views.py", 1), ("app/web/views.py", 2), ("app/web/views.py", 3)])

    def test_banned_pattern_only_in_included_files(self) -> None:
        self.rules({"id": "R-003", "kind": "ban-pattern", "include": ["src/**/*.tsx"], "pattern": r"\buseEffect\("})
        self.write("src/ui/a.tsx", "useEffect(() => {});\n")
        self.write("lib/a.tsx", "useEffect(() => {});\n")
        self.assertEqual(self.lines(), [("src/ui/a.tsx", 1)])

    def test_message_reaches_the_agent(self) -> None:
        self.rules({"id": "R-003", "kind": "ban-pattern", "include": ["**/*.py"], "pattern": "eval\\("})
        self.write("a.py", "eval('1')\n")
        code, out = self.kit("check")
        self.assertEqual(code, 3)
        self.assertIn(MESSAGE, out["violations"][0]["message"])

    def test_baseline_tolerates_old_violations_and_fails_new_ones(self) -> None:
        self.rules({"id": "R-001", "kind": "ban-comments", "include": ["**/*.py"]})
        self.write("old.py", "# one\n# two\n")
        self.assertEqual(self.kit("baseline")[0], 0)
        code, out = self.kit("check")
        self.assertEqual((code, out["tolerated_by_baseline"]), (0, 2))
        self.write("old.py", "# one\n# two\n# three\n")
        self.assertEqual(self.kit("check")[0], 3)
        self.write("new.py", "# fresh\n")
        self.write("old.py", "# one\n")
        self.assertEqual(self.lines(), [("new.py", 1)])

    def test_baseline_only_shrinks_without_the_owner(self) -> None:
        self.rules({"id": "R-001", "kind": "ban-comments", "include": ["**/*.py"]})
        self.write("a.py", "# one\n")
        self.kit("baseline")
        self.write("a.py", "# one\n# two\n")
        code, out = self.kit("baseline")
        self.assertEqual(code, 2)
        self.assertIn("only shrinks", out["error"])
        self.assertEqual(self.kit("baseline", "--owner-approved")[0], 0)
        self.write("a.py", "x = 1\n")
        self.assertEqual(self.kit("baseline")[0], 0)
        self.assertEqual(json.loads((self.repo / ".governance/baseline.json").read_text())["counts"], {})

    def test_explicit_path_ignores_include_exclude_and_baseline(self) -> None:
        self.rules({"id": "R-001", "kind": "ban-comments", "include": ["src/**/*.py"]})
        self.write(".governance/bad/R-001.py", "# excuse\n")
        self.assertEqual(self.kit("check")[0], 0)
        self.assertEqual(self.kit("check", "--rule", "R-001", ".governance/bad/R-001.py")[0], 3)

    def test_alias_checks_a_bad_example_as_if_it_lived_in_the_guarded_directory(self) -> None:
        self.rules({"id": "R-002", "kind": "ban-import", "include": ["src/renderer/**"], "forbid": ["src/main"]})
        self.write(".governance/bad/R-002.ts", "import { db } from '../main/db';\n")
        self.assertEqual(self.kit("check", "--rule", "R-002", ".governance/bad/R-002.ts")[0], 0)
        self.assertEqual(self.kit("check", "--rule", "R-002", "--as", "src/renderer/x.ts",
                                  ".governance/bad/R-002.ts")[0], 3)

    def test_git_ignored_and_excluded_files_are_skipped(self) -> None:
        self.rules({"id": "R-001", "kind": "ban-comments", "include": ["**/*.py"]}, exclude=["vendor/**"])
        self.write(".gitignore", "build/\n")
        self.write("build/a.py", "# generated\n")
        self.write("vendor/a.py", "# third party\n")
        self.assertEqual(self.kit("check")[0], 0)

    def test_invalid_configuration_is_refused(self) -> None:
        self.assertEqual(self.kit("check")[0], 2)
        self.rules({"id": "R-001", "kind": "ban-everything", "include": ["**"]})
        self.assertEqual(self.kit("check")[0], 2)
        self.write(".governance/rules.json", json.dumps({"version": 1, "rules": [
            {"id": "R-001", "kind": "ban-pattern", "include": ["**"], "pattern": "x", "message": "no"}]}))
        self.assertIn("what to do instead", self.kit("check")[1]["error"])
        self.rules({"id": "R-001", "kind": "ban-pattern", "include": ["**"], "pattern": "("})
        self.assertEqual(self.kit("check")[0], 2)
        self.rules({"id": "R-001", "kind": "ban-pattern", "include": ["**"], "pattern": "x"})
        self.assertEqual(self.kit("check", "--rule", "R-999")[0], 2)


if __name__ == "__main__":
    unittest.main()
