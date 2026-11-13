#!/usr/bin/env python3
"""The one path: the planning skills, the front door, and the script that says where a project is."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
SKILLS = PACKAGE / "skills"
WHERE = PACKAGE / "scripts" / "where"
LINK = re.compile(r"\]\((?!https?:|#|mailto:)([^)#\s]+)(?:#[^)]*)?\)")
DROPPED = ("ask-matt", "setup-matt-pocock-skills", "Skill tool", "intent-help", "govern-help", "setup-intent",
           "`governance` plugin", "`intent` plugin")
PLANNING = ("grilling", "grill-me", "grill-with-docs", "domain-modeling", "need-first", "stack", "to-spec", "to-tickets",
            "wayfinder", "triage", "research", "prototype", "implement", "implement-spec", "setup-project")


def read(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


class PathSkillTests(unittest.TestCase):
    def documents(self) -> list[Path]:
        return [p for p in sorted(SKILLS.rglob("*.md")) if "node_modules" not in p.parts]

    def test_relative_links_in_the_planning_and_help_skills_resolve(self) -> None:
        broken = []
        for name in (*PLANNING, "start", "next", "trust-help", "adopt", "approve", "stage"):
            for path in sorted((SKILLS / name).rglob("*.md")):
                fenced = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
                for target in LINK.findall(fenced):
                    if "<" not in target and not (path.parent / target).exists():
                        broken.append(f"{path.relative_to(PACKAGE).as_posix()} -> {target}")
        self.assertEqual(broken, [])

    def test_nothing_names_the_two_plugins_this_one_replaced(self) -> None:
        for path in [*self.documents(), PACKAGE / "README.md", PACKAGE / "docs" / "GUIDE.md"]:
            text = path.read_text(encoding="utf-8")
            for word in DROPPED:
                self.assertNotIn(word, text, f"{path.relative_to(PACKAGE).as_posix()}: {word}")

    def test_the_owner_needs_three_commands_and_one_path(self) -> None:
        steps = (SKILLS / "start" / "STEPS.md").read_text(encoding="utf-8")
        for needed in ("| 1 | Describe |", "| 2 | Choose the stack |", "| 3 | Spec |", "| 4 | Tickets |", "| 5 | Build |",
                       "| 6 | Merge |", "`Step N of 6: <Name>.`", "`You:`", "`Next:`"):
            self.assertIn(needed, steps)
        for name in ("start", "next", "trust-help"):
            self.assertIn("disable-model-invocation: true", read(name).split("\n---\n", 1)[0], name)
        for name in ("start", "next", "stack", "to-spec", "to-tickets", "implement", "stage", "approve", "adopt"):
            self.assertIn("STEPS.md", read(name), name)
        for needed in ("scripts/where", "**adopt** skill", "**implement** skill", "**stack** skill", "**to-spec** skill",
                       "**to-tickets** skill"):
            self.assertIn(needed, read("next"))
        self.assertIn("Do not adopt the rules now", read("start"))

    def test_building_a_ticket_always_runs_inside_a_stage(self) -> None:
        text = read("implement")
        self.assertIn("`govern` skill", text)
        self.assertIn("`adopt` skill first", text)
        self.assertIn("Never build a ticket outside a stage", text)

    def test_setup_respects_the_stage_requirement(self) -> None:
        text = read("setup-project")
        for glob in ("GLOSSARY.md", "**/GLOSSARY.md", "docs/adr/**", "docs/agents/**", ".scratch/**"):
            self.assertIn(f"`{glob}`", text)
        self.assertIn("you cannot edit that config yourself", text)

    def test_the_interview_asks_through_the_question_tool_and_tests_each_need(self) -> None:
        self.assertIn("If you have a tool for asking the user questions, use it for every round", read("grilling"))
        self.assertEqual(read("wayfinder").count("`grilling`, `domain-modeling` and `need-first`"), 3)

    def test_tickets_account_for_every_story_before_publishing(self) -> None:
        text = read("to-tickets")
        for needed in ("### 4. Check coverage", "List every story number in order", "## Covers",
                       "Do not publish while a story is uncovered", "Before Building"):
            self.assertIn(needed, text)

    def test_a_new_product_gets_a_stack_before_a_spec(self) -> None:
        self.assertNotIn("disable-model-invocation", read("stack").split("\n---\n", 1)[0])
        for name, needed in (("stack", "## 4. List what the owner must set up before building"), ("grilling", "`stack` skill"),
                             ("wayfinder", "`stack` skill"), ("to-spec", "## Before Building"), ("to-spec", "Technology stack")):
            self.assertIn(needed, read(name), name)


def issue(number: int, title: str, body: str, state: str = "open", labels: tuple[str, ...] = (),
          blocked_by: tuple[int, ...] = ()) -> dict:
    return {"number": number, "title": title, "body": body, "state": state,
            "labels": [{"name": name} for name in labels], "blocked_by": list(blocked_by)}


SPEC = issue(11, "Spec: reports", "## Problem Statement\n\n## User Stories\n\n1. As a reporter")
TICKET = "## Parent\n\n#11\n\n## What to build\n\n## Acceptance criteria\n\n- [ ] one"


class WhereTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.git("commit", "-q", "--allow-empty", "-m", "base")

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], check=True)

    def where(self, issues: list[dict] | None = None, pulls: list[dict] | None = None) -> dict:
        tracker = self.repo.parent / (self.repo.name + "-tracker.json")
        self.addCleanup(tracker.unlink, True)
        tracker.write_text(json.dumps({"issues": issues or [], "pulls": pulls or []}), encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(WHERE), "--repo", str(self.repo), "--json", "--tracker-file", str(tracker)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def write(self, name: str, text: str) -> None:
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_an_empty_project_is_at_describe(self) -> None:
        report = self.where()
        self.assertEqual((report["step"], report["name"]), (1, "Describe"))
        self.assertIn("/start", report["next"])

    def test_a_started_interview_stays_at_describe(self) -> None:
        self.write("GLOSSARY.md", "# words\n")
        self.assertEqual(self.where()["step"], 1)

    def test_a_spec_with_no_code_and_no_stack_is_at_choose_the_stack(self) -> None:
        report = self.where([SPEC])
        self.assertEqual((report["step"], report["next"]), (2, "/stack"))

    def test_a_recorded_stack_with_no_spec_is_at_spec(self) -> None:
        self.write("docs/adr/0001-stack.md", "# Technology stack\n\nPython.\n")
        report = self.where()
        self.assertEqual((report["step"], report["next"]), (3, "/to-spec"))

    def test_a_spec_and_stack_with_no_tickets_is_at_tickets(self) -> None:
        self.write("docs/adr/0001-stack.md", "# Technology stack\n\nPython.\n")
        report = self.where([SPEC])
        self.assertEqual((report["step"], report["next"]), (4, "/to-tickets 11"))

    def test_the_first_unblocked_agent_ticket_is_next_and_owner_tickets_are_named(self) -> None:
        self.write("docs/adr/0001-stack.md", "# Technology stack\n\nPython.\n")
        tickets = [issue(12, "Prove the send path", TICKET, labels=("ready-for-human",)),
                   issue(13, "File a daily report", TICKET, labels=("ready-for-agent",)),
                   issue(14, "Send a report", TICKET, labels=("ready-for-agent",), blocked_by=(12, 13))]
        report = self.where([SPEC, *tickets])
        self.assertEqual((report["step"], report["next"]), (5, "/implement 13"))
        self.assertIn("#12 Prove the send path", report["you"])
        self.assertIn("/adopt runs first", report["state"])
        self.assertIn("3 of 3 tickets are still open", report["state"])

    def test_code_without_strict_rules_asks_for_adoption_again(self) -> None:
        self.write("docs/adr/0001-stack.md", "# Technology stack\n\nPython.\n")
        self.write(".governance/config.json", json.dumps({"version": 1, "require_stage": True}))
        self.write(".governance/rules.json", json.dumps({"version": 1, "rules": [{"id": "R-001", "kind": "ban-comments"}]}))
        self.write("app/main.py", "VALUE = 1\n")
        report = self.where([SPEC, issue(13, "File a daily report", TICKET)])
        self.assertEqual(report["facts"]["strict_rules_missing"], ["Python"])
        self.assertIn("Strict rules for Python", report["state"])

    def test_when_only_owner_tickets_are_free_it_waits_on_the_owner(self) -> None:
        self.write("docs/adr/0001-stack.md", "# Technology stack\n\nPython.\n")
        tickets = [issue(12, "Prove the send path", TICKET, labels=("ready-for-human",)),
                   issue(14, "Send a report", TICKET, blocked_by=(12,))]
        report = self.where([SPEC, *tickets])
        self.assertEqual(report["step"], 5)
        self.assertIn("#12", report["you"])
        self.assertEqual(report["next"], "wait for the owner")

    def test_an_open_pull_request_is_at_merge_and_a_research_branch_is_not(self) -> None:
        self.write("docs/adr/0001-stack.md", "# Technology stack\n\nPython.\n")
        tickets = [SPEC, issue(13, "File a daily report", TICKET)]
        research = [{"number": 20, "title": "notes", "branch": "research/mailbox"}]
        self.assertEqual(self.where(tickets, research)["step"], 5)
        report = self.where(tickets, [{"number": 21, "title": "File a daily report", "branch": "ticket-13"}])
        self.assertEqual(report["step"], 6)
        self.assertIn("#21", report["you"])

    def test_all_tickets_closed_finishes_the_spec(self) -> None:
        self.write("docs/adr/0001-stack.md", "# Technology stack\n\nPython.\n")
        report = self.where([SPEC, issue(13, "File a daily report", TICKET, state="closed")])
        self.assertEqual(report["step"], 6)
        self.assertIn("close spec #11", report["next"])

    def test_an_active_stage_comes_before_everything_else(self) -> None:
        contract = {"version": 1, "name": "Totals slice", "review": "none", "intent": "Booking totals multiply days by the daily rate.",
                    "inputs": [], "outputs": [],
                    "acceptance": [{"id": "AC-001", "description": "The check script exits zero", "checks": ["CHK-001"]}],
                    "checks": [{"id": "CHK-001", "argv": [sys.executable, "-c", "pass"], "timeout_seconds": 30}]}
        self.write("stage.json", json.dumps(contract))
        subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts" / "stagectl"), "--repo", str(self.repo), "freeze",
                        "--contract", "stage.json", "--owner-approved"], check=True, capture_output=True)
        report = self.where([SPEC], [{"number": 21, "title": "x", "branch": "b"}])
        self.assertEqual(report["step"], 5)
        self.assertIn("Totals slice", report["state"])

    @unittest.skipIf(os.name == "nt", "builds a PATH with a fake gh script")
    def test_github_is_read_page_by_page_with_any_gh_and_a_failure_is_named(self) -> None:
        self.git("remote", "add", "origin", "https://github.com/owner/project.git")
        bin_dir = self.repo.parent / (self.repo.name + "-bin")
        bin_dir.mkdir()
        self.addCleanup(shutil.rmtree, bin_dir, True)
        log = bin_dir / "calls.log"
        fake = bin_dir / "gh"
        fake.write_text(f"""#!{sys.executable}
import json, sys, re
args = sys.argv[1:]
open({str(log)!r}, "a").write(" ".join(args) + "\\n")
if "--slurp" in args or "--paginate" in args:
    sys.stderr.write("unknown flag\\n"); sys.exit(1)
if {str(bin_dir / "fail")!r} and __import__("os").path.exists({str(bin_dir / "fail")!r}):
    sys.stderr.write("HTTP 401: Bad credentials\\n"); sys.exit(1)
path = args[1]
page = int(re.search(r"[?&]page=(\\d+)", path).group(1))
if "/issues?" in path:
    count = 100 if page == 1 else 1 if page == 2 else 0
    print(json.dumps([{{"number": page * 1000 + n, "title": "x", "body": "", "state": "closed", "labels": []}} for n in range(count)]))
else:
    print("[]")
""", encoding="utf-8")
        fake.chmod(0o755)
        env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        run = lambda: json.loads(subprocess.run([sys.executable, "-B", str(WHERE), "--repo", str(self.repo), "--json"],
                                                capture_output=True, text=True, check=True, env=env).stdout)
        report = run()
        self.assertNotIn("could not be read", report["state"])
        self.assertIn("page=2", log.read_text())
        (bin_dir / "fail").write_text("", encoding="utf-8")
        report = run()
        self.assertIn("could not be read", report["state"])
        self.assertIn("Bad credentials", report["state"])

    def test_the_plain_report_is_three_lines_a_person_can_read(self) -> None:
        result = subprocess.run([sys.executable, "-B", str(WHERE), "--repo", str(self.repo), "--tracker-file", "/nonexistent"],
                                capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        tracker = self.repo.parent / (self.repo.name + "-t.json")
        self.addCleanup(tracker.unlink, True)
        tracker.write_text(json.dumps({"issues": [], "pulls": []}), encoding="utf-8")
        out = subprocess.run([sys.executable, "-B", str(WHERE), "--repo", str(self.repo), "--tracker-file", str(tracker)],
                             capture_output=True, text=True, check=True).stdout.splitlines()
        self.assertEqual(len(out), 3)
        self.assertTrue(out[0].startswith("Step 1 of 6: Describe."))
        self.assertTrue(out[1].startswith("You: "))
        self.assertTrue(out[2].startswith("Next: "))


if __name__ == "__main__":
    unittest.main()
