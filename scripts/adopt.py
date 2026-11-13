#!/usr/bin/env python3
"""Set a project up to be governed: enforcers, a starter rule, and a merge gate.

Run once per project, by the owner, from a checkout of this plugin:

    python scripts/adopt.py --repo path/to/project

It adds, and never overwrites an existing file except its own copied tools:
  tools/governance/                  stagectl, verifyctl, rulectl, rulekit, for CI and the terminal
  .governance/config.json            require_stage: agents may not change files outside a stage
  .governance/rules.json             starter rules: no comments, no file over 400 lines, and the
                                     strictest standard linter and type checker for the language
  .governance/bad/R-*.*              a committed example of each mistake, used as the rule's proof
  ruff.toml, eslint.config.mjs       strict linter settings, only when the project has none
  .governance/baseline.json          today's violations, so only new ones fail
  AGENTS.md                          a `## Rules` table listing the starter rules
  .github/workflows/governance.yml   runs the rules and the stage gate on every pull request
  .gitignore                         ignores .verify/ (evidence stays out of the code fingerprint)

Run it again after updating the plugin to refresh tools/governance/, or after the project gains
a language: the strict rules for that language are added then. Standard library only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent
TOOLS = ("stagectl", "verifyctl", "rulectl", "rulekit")
LANGUAGES = {".py": "py", ".ts": "ts", ".tsx": "ts", ".js": "js", ".jsx": "js", ".mjs": "js", ".go": "go",
             ".rs": "rs", ".java": "java", ".kt": "kt", ".cs": "cs", ".swift": "swift", ".dart": "dart"}
BAD = {"py": "# Retry because the first call sometimes fails.\nVALUE = 1\n"}
BAD_C_STYLE = "// Retry because the first call sometimes fails.\n"
MAX_LINES = 400
SPLIT = ("Split this file: move one responsibility into its own module beside it and import it. "
         "Never add to a file that is over the limit.")
RUFF_TOML = """line-length = 120
extend-exclude = ["tools/governance", ".governance"]

[lint]
select = ["E", "F", "W", "B", "C90", "N", "UP", "SIM", "RET", "ARG", "PL", "RUF", "BLE", "T20", "ERA"]

[lint.mccabe]
max-complexity = 10
"""
ESLINT_CONFIG = """import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist/**", "build/**", "coverage/**", "tools/governance/**"] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  {
    rules: {
      complexity: ["error", 10],
      "max-depth": ["error", 4],
      "max-params": ["error", 4],
      eqeqeq: ["error", "always"],
    },
  },
);
"""
ESLINT_CONFIGS = ("eslint.config.js", "eslint.config.mjs", "eslint.config.cjs", "eslint.config.ts", "eslint.config.mts")
ESLINT_INSTALL = "npm install --save-dev eslint @eslint/js typescript-eslint typescript"
PRESETS = {
    "ruff": {
        "rule": "The linter's strict rule set holds", "level": "lint", "ext": "py",
        "bad": "import os\n\n\ndef load():\n    try:\n        return open('data.txt').read()\n    except:\n        return None\n",
        "entry": {"kind": "linter", "argv": ["ruff", "check", "--output-format", "concise", "--no-fix", "--quiet"],
                  "target": ["."], "include": ["**/*.py"], "install": "Install it with: pip install ruff",
                  "message": "Fix the code the way the finding says. Never silence it with noqa or a config change."}},
    "mypy": {
        "rule": "Every function is fully typed and the strict type check passes", "level": "types", "ext": "py",
        "bad": "def total(prices):\n    return sum(prices)\n",
        "entry": {"kind": "linter", "argv": ["mypy", "--strict", "--no-error-summary", "--explicit-package-bases"],
                  "target": ["."], "include": ["**/*.py"], "install": "Install it with: pip install mypy",
                  "message": "Give the value its real type. Never use Any, a cast or type: ignore to get past it."}},
    "tsc": {
        "rule": "The strict type check passes", "level": "types", "ext": "ts",
        "bad": "export function total(prices) {\n  return prices.length;\n}\n",
        "entry": {"kind": "linter", "argv": ["npx", "--no-install", "tsc", "--noEmit", "--pretty", "false", "--strict",
                                             "--noUncheckedIndexedAccess", "--noImplicitOverride",
                                             "--noFallthroughCasesInSwitch"],
                  "include": ["**/*.ts", "**/*.tsx", "**/*.mts", "**/*.cts"],
                  "install": "Install it with: npm install --save-dev typescript",
                  "message": "Give the value its real type. Never use any, a cast or @ts-ignore to get past it."}},
    "eslint": {
        "rule": "The linter's strict rule set holds", "level": "lint", "ext": "js",
        "bad": "export function same(a, b) {\n  var unused = 1;\n  return a == b;\n}\n",
        "entry": {"kind": "linter", "format": "eslint-json", "argv": ["npx", "--no-install", "eslint", "--format", "json"],
                  "target": ["."], "include": ["**/*.js", "**/*.jsx", "**/*.mjs", "**/*.cjs", "**/*.ts", "**/*.tsx"],
                  "install": f"Install it with: {ESLINT_INSTALL}",
                  "message": "Fix the code the way the finding says. Never silence it with eslint-disable."}},
}
MESSAGE = ("Delete the comment. Say it with a clearer name, a type or a test; if the code needs an excuse, "
           "fix the code.")
WORKFLOW = """name: governance

on:
  pull_request:

permissions:
  contents: read

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          # The pull request's own commit, not GitHub's merge preview: a receipt names exact code.
          ref: ${{{{ github.event.pull_request.head.sha }}}}
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
{setup}      - name: Rules hold
        run: python tools/governance/rulekit check
      - name: Every rule names an enforcer that rejects its bad example
        run: python tools/governance/rulectl check --repo . --prove
      - name: A stage receipt proves this exact code
        # Add --rerun, after installing the project's dependencies above, to make CI
        # run the receipt's checks itself instead of trusting the recorded result.
        run: python tools/governance/stagectl gate --base "origin/${{{{ github.base_ref }}}}" --markdown "$GITHUB_STEP_SUMMARY"
"""
RULES_SECTION = """
## Rules

Each rule names the file that enforces it and a command that proves the enforcer
rejects a committed bad example. `python tools/governance/rulectl check --repo . --prove`
verifies this table; `python tools/governance/rulekit check` runs the rules.

| ID | Rule | Level | Enforced by | Proof | Notes |
|---|---|---|---|---|---|
"""
ROW = ("| {id} | {rule} | {level} | `.governance/rules.json` | `python tools/governance/rulekit check --rule {id} {bad}` "
       "| Older cases are tolerated by `.governance/baseline.json` until cleaned up |\n")
PYTHON_SETUP = """      - name: Python linters
        run: |
          pip install ruff mypy
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
"""
NODE_SETUP = """      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - name: Node dependencies
        run: npm ci
"""


PLANNING_DOCS = ("GLOSSARY.md", "GLOSSARY-MAP.md", "**/GLOSSARY.md", "docs/adr/**", "**/docs/adr/**",
                 "docs/agents/**", ".scratch/**")

def tracked_files(repo: Path) -> list[str]:
    result = subprocess.run(["git", "-C", str(repo), "ls-files", "-co", "--exclude-standard"],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"{repo} is not a Git repository")
    return result.stdout.splitlines()


def create(path: Path, text: str, done: list[str]) -> bool:
    if path.exists():
        done.append(f"kept     {path.name} (already present)")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    done.append(f"created  {path}")
    return True


def upgrade(path: Path, globs: list[str], chosen: list[str],
            done: list[str]) -> tuple[list[tuple[str, str, str, str]], dict[str, str], dict[str, list[str]]]:
    """Bring an adopted project's rules up to the languages it has now. Returns the new table rows,
    the new bad examples and, for each rule added or widened, the file endings it newly covers
    (empty for a new rule, which covers everything it finds)."""
    config = json.loads(path.read_text(encoding="utf-8"))
    rules = config.setdefault("rules", [])
    changed: dict[str, list[str]] = {}
    for rule in rules:
        missing = [glob for glob in globs if glob not in rule.get("include", [])]
        if missing and rule.get("id") in ("R-001", "R-002") and rule.get("kind") in ("ban-comments", "max-lines"):
            rule["include"] = [*rule.get("include", []), *missing]
            changed[rule["id"]] = [glob.rsplit("*", 1)[-1] for glob in missing]
    have = {word for rule in rules for word in rule.get("argv", []) if word in PRESETS}
    numbers = [int(str(rule.get("id", ""))[2:]) for rule in rules if str(rule.get("id", ""))[2:].isdigit()]
    rows, examples = [], {}
    for name in chosen:
        if name in have:
            continue
        preset = PRESETS[name]
        numbers.append(max(numbers, default=0) + 1)
        rule_id = f"R-{numbers[-1]:03d}"
        bad = f".governance/bad/{rule_id}.{preset['ext']}"
        rules.append({"id": rule_id, **preset["entry"]})
        rows.append((rule_id, preset["rule"], preset["level"], bad))
        examples[bad] = preset["bad"]
        changed[rule_id] = []
    if changed:
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n")
        done.append(f"updated  {path} ({', '.join(sorted(changed))} now cover the languages in this project)")
    return rows, examples, changed


def rebaseline(repo: Path, tools: Path, changed: dict[str, list[str]], done: list[str]) -> str:
    """Record today's violations. On a project that has a baseline, only the rules in `changed` may add to it."""
    path = repo / ".governance" / "baseline.json"
    previous = json.loads(path.read_text(encoding="utf-8")).get("counts", {}) if path.exists() else None
    argv = [sys.executable, "-B", str(tools / "rulekit"), "--repo", str(repo), "baseline"]
    result = subprocess.run(argv + ([] if previous is None else ["--owner-approved"]),
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return result.stderr.strip() or result.stdout.strip()
    if previous is None:
        done.append(f"created  {path}")
        return ""
    value = json.loads(path.read_text(encoding="utf-8"))
    for rule, files in list(value["counts"].items()):
        if rule in changed and not changed[rule]:
            continue
        endings = tuple(changed.get(rule, []))
        kept = {name: count if endings and name.endswith(endings) else min(count, previous.get(rule, {}).get(name, 0))
                for name, count in files.items()}
        value["counts"][rule] = {name: count for name, count in kept.items() if count}
        if not value["counts"][rule]:
            del value["counts"][rule]
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    done.append(f"updated  {path} (today's violations of {', '.join(sorted(changed))})")
    return ""


def add_rows(agents: Path, text: str, rows: list[tuple[str, str, str, str]], done: list[str]) -> None:
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip().lower() == "## rules")
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
    table = [index for index in range(start, end) if lines[index].startswith("|")]
    rows = [row for row in rows if not any(line.startswith(f"| {row[0]} ") for line in lines)]
    if not rows:
        done.append("kept     AGENTS.md (it already has a Rules section)")
        return
    if not table:
        done.append(f"NOT DONE AGENTS.md has a Rules section with no table; add rows for {', '.join(r[0] for r in rows)}")
        return
    added = [ROW.format(id=i, rule=r, level=l, bad=b).rstrip("\n") for i, r, l, b in rows]
    lines[table[-1] + 1:table[-1] + 1] = added
    agents.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    done.append(f"added    {', '.join(row[0] for row in rows)} to the Rules table in {agents}")


def add_setup(workflow: Path, parts: list[str], done: list[str]) -> None:
    text = workflow.read_text(encoding="utf-8")
    marker = "      - name: Rules hold\n"
    missing = [part for part in parts if part.splitlines()[0] not in text]
    if not missing or marker not in text:
        return
    workflow.write_text(text.replace(marker, "".join(missing) + marker, 1), encoding="utf-8", newline="\n")
    done.append(f"updated  {workflow} (it now installs the linters the rules need)")


def adopt(repo: Path) -> list[str]:
    done: list[str] = []
    files = tracked_files(repo)
    tools = repo / "tools" / "governance"
    tools.mkdir(parents=True, exist_ok=True)
    for name in TOOLS:
        shutil.copy2(SOURCE / name, tools / name)
    done.append(f"copied   {', '.join(TOOLS)} to {tools}")

    present = sorted({LANGUAGES[Path(name).suffix] for name in files
                      if Path(name).suffix in LANGUAGES and not name.startswith(("tools/governance/", ".governance/"))})
    suffixes = sorted(suffix for suffix, language in LANGUAGES.items() if language in present) or [".py"]
    language = "py" if "py" in present or not present else present[0]
    governance = repo / ".governance"
    globs = [f"**/*{suffix}" for suffix in suffixes]
    rules: list[dict] = [
        {"id": "R-001", "kind": "ban-comments", "include": globs,
         "allow": ["^(eslint-|@ts-|type:|noqa|pragma|pylint:|go:|nolint|SPDX-)"], "message": MESSAGE},
        {"id": "R-002", "kind": "max-lines", "max": MAX_LINES, "include": globs, "message": SPLIT}]
    rows = [("R-001", "Source files carry no comments", "lint", f".governance/bad/R-001.{language}"),
            ("R-002", f"No source file is longer than {MAX_LINES} lines", "lint", f".governance/bad/R-002.{language}")]
    examples = {rows[0][3]: BAD.get(language, BAD_C_STYLE),
                rows[1][3]: "".join(f"VALUE_{n} = {n}\n" if language == "py" else f"const value{n} = {n};\n"
                                    for n in range(MAX_LINES + 1))}
    node = (repo / "package.json").is_file() and bool({"ts", "js"} & set(present))
    chosen = []
    if "py" in present:
        if not any((repo / name).exists() for name in ("ruff.toml", ".ruff.toml")) and \
                "[tool.ruff" not in ((repo / "pyproject.toml").read_text(encoding="utf-8")
                                     if (repo / "pyproject.toml").is_file() else ""):
            create(repo / "ruff.toml", RUFF_TOML, done)
        chosen += ["ruff", "mypy"]
    if node:
        if "ts" in present and (repo / "tsconfig.json").is_file():
            chosen.append("tsc")
        if not any((repo / name).exists() for name in ESLINT_CONFIGS):
            create(repo / "eslint.config.mjs", ESLINT_CONFIG, done)
        chosen.append("eslint")
    for name in chosen:
        preset = PRESETS[name]
        rule_id = f"R-{len(rules) + 1:03d}"
        bad = f".governance/bad/{rule_id}.{preset['ext']}"
        rules.append({"id": rule_id, **preset["entry"]})
        rows.append((rule_id, preset["rule"], preset["level"], bad))
        examples[bad] = preset["bad"]
    create(governance / "config.json", json.dumps({"version": 1, "require_stage": True, "exempt": list(PLANNING_DOCS), "protected": []}, indent=2) + "\n", done)
    fresh = create(governance / "rules.json", json.dumps(
        {"version": 1, "exclude": ["tools/governance/**"], "rules": rules}, indent=2) + "\n", done)
    changed: dict[str, list[str]] = {}
    if not fresh:
        rows, examples, changed = upgrade(governance / "rules.json", globs if present else [], chosen, done)
    for bad, text in examples.items():
        if fresh or not (repo / bad).exists():
            create(repo / bad, text, done)
    pending = ""
    if changed or not (governance / "baseline.json").exists():
        pending = rebaseline(repo, tools, changed, done)

    agents = repo / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.exists() else "# Agent guide\n"
    if any(line.strip().lower() == "## rules" for line in text.splitlines()):
        add_rows(agents, text, rows if not fresh else [], done)
    else:
        table = RULES_SECTION + "".join(ROW.format(id=i, rule=r, level=l, bad=b) for i, r, l, b in rows)
        agents.write_text(text.rstrip("\n") + "\n" + table, encoding="utf-8", newline="\n")
        done.append(f"added    a Rules table to {agents}")

    setup = (PYTHON_SETUP if "py" in present else "") + (NODE_SETUP if node else "")
    workflow = repo / ".github" / "workflows" / "governance.yml"
    if not create(workflow, WORKFLOW.format(setup=setup), done):
        add_setup(workflow, [part for part in ((PYTHON_SETUP if "py" in present else ""), (NODE_SETUP if node else "")) if part], done)
    ignore = repo / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    if ".verify/" not in lines:
        ignore.write_text("\n".join([*lines, ".verify/"]) + "\n", encoding="utf-8", newline="\n")
        done.append("added    .verify/ to .gitignore")
    if pending:
        done.append(f"\nNOT DONE the baseline could not be recorded: {pending}")
        if node:
            done.append(f"         for a JavaScript or TypeScript project, first run: {ESLINT_INSTALL}")
        approval = " --owner-approved" if (governance / "baseline.json").exists() else ""
        done.append(f"         install what is missing, then run: python tools/governance/rulekit baseline{approval}")
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".", help="the project to set up")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    for line in adopt(repo):
        print(line)
    print("\nNext: review and commit these files, then make the `gate` job a required check on your main branch.")
    print("Loosen .governance/config.json (exempt globs, or require_stage false) if every edit needing a stage is too strict.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
