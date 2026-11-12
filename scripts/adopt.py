#!/usr/bin/env python3
"""Set a project up to be governed: enforcers, a starter rule, and a merge gate.

Run once per project, by the owner, from a checkout of this plugin:

    python scripts/adopt.py --repo path/to/project

It adds, and never overwrites an existing file except its own copied tools:
  tools/governance/                  stagectl, verifyctl, rulectl, rulekit, for CI and the terminal
  .governance/config.json            require_stage: agents may not change files outside a stage
  .governance/rules.json             starter rule R-001: no comments in source files
  .governance/bad/R-001.*            a committed example of the mistake, used as the rule's proof
  .governance/baseline.json          today's violations, so only new ones fail
  AGENTS.md                          a `## Rules` table listing R-001
  .github/workflows/governance.yml   runs the rules and the stage gate on every pull request
  .gitignore                         ignores .verify/ (evidence stays out of the code fingerprint)

Run it again after updating the plugin to refresh tools/governance/. Standard library only.
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
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Rules hold
        run: python tools/governance/rulekit check
      - name: Every rule names an enforcer that rejects its bad example
        run: python tools/governance/rulectl check --repo . --prove
      - name: A stage receipt proves this exact code
        # Add --rerun, after installing the project's dependencies above, to make CI
        # run the receipt's checks itself instead of trusting the recorded result.
        run: python tools/governance/stagectl gate --base "origin/${{ github.base_ref }}" --markdown "$GITHUB_STEP_SUMMARY"
"""
RULES_SECTION = """
## Rules

Each rule names the file that enforces it and a command that proves the enforcer
rejects a committed bad example. `python tools/governance/rulectl check --repo . --prove`
verifies this table; `python tools/governance/rulekit check` runs the rules.

| ID | Rule | Level | Enforced by | Proof | Notes |
|---|---|---|---|---|---|
| R-001 | Source files carry no comments | lint | `.governance/rules.json` | `python tools/governance/rulekit check --rule R-001 {bad}` | Existing comments are tolerated by `.governance/baseline.json` until cleaned up |
"""


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
    bad = f".governance/bad/R-001.{language}"
    governance = repo / ".governance"
    create(governance / "config.json", json.dumps({"version": 1, "require_stage": True, "exempt": []}, indent=2) + "\n", done)
    create(governance / "rules.json", json.dumps({"version": 1, "exclude": ["tools/governance/**"], "rules": [{
        "id": "R-001", "kind": "ban-comments", "include": [f"**/*{suffix}" for suffix in suffixes],
        "allow": ["^(eslint-|@ts-|type:|noqa|pragma|pylint:|go:|nolint|SPDX-)"], "message": MESSAGE}]}, indent=2) + "\n", done)
    create(repo / bad, BAD.get(language, BAD_C_STYLE), done)
    if not (governance / "baseline.json").exists():
        subprocess.run([sys.executable, "-B", str(tools / "rulekit"), "--repo", str(repo), "baseline"], check=True,
                       capture_output=True)
        done.append(f"created  {governance / 'baseline.json'}")

    agents = repo / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.exists() else "# Agent guide\n"
    if any(line.strip().lower() == "## rules" for line in text.splitlines()):
        done.append("kept     AGENTS.md (it already has a Rules section)")
    else:
        agents.write_text(text.rstrip("\n") + "\n" + RULES_SECTION.format(bad=bad), encoding="utf-8", newline="\n")
        done.append(f"added    a Rules table to {agents}")

    create(repo / ".github" / "workflows" / "governance.yml", WORKFLOW, done)
    ignore = repo / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    if ".verify/" not in lines:
        ignore.write_text("\n".join([*lines, ".verify/"]) + "\n", encoding="utf-8", newline="\n")
        done.append("added    .verify/ to .gitignore")
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
