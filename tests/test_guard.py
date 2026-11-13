#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
GUARD = PACKAGE / "hooks" / "guard.py"
STAGECTL = PACKAGE / "scripts" / "stagectl"

CONTRACT = {
    "version": 1, "name": "Totals slice", "review": "none",
    "intent": "Booking totals multiply days by the daily rate.",
    "inputs": [], "outputs": [],
    "acceptance": [{"id": "AC-001", "description": "The check script exits zero", "checks": ["CHK-001"]}],
    "checks": [{"id": "CHK-001", "argv": [sys.executable, "-c", "pass"], "timeout_seconds": 30}],
}


class GuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "stage.json").write_text(json.dumps(CONTRACT), encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "-q", "--allow-empty", "-m", "base"], check=True)

    def hook(self, event: str, payload: object) -> dict:
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        result = subprocess.run([sys.executable, "-B", str(GUARD), event], input=raw, capture_output=True, check=False,
                                env={**os.environ, "CURSOR_PROJECT_DIR": str(self.repo)})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def shell(self, command: str) -> dict:
        return self.hook("pre-tool-use", {"tool_name": "Shell", "tool_input": {"command": command}})

    def stagectl(self, *args: str) -> None:
        subprocess.run([sys.executable, "-B", str(STAGECTL), "--repo", str(self.repo), *args], check=True,
                       capture_output=True)

    def freeze(self) -> None:
        self.stagectl("freeze", "--contract", "stage.json", "--owner-approved")

    def approve(self, text: str = "/approve", conversation: str = "c1") -> dict:
        return self.hook("before-submit-prompt", {"prompt": text, "conversation_id": conversation,
                                                  "workspace_roots": [str(self.repo)]})

    def approval_command(self, command: str, conversation: str = "c1") -> dict:
        return self.hook("pre-tool-use", {"tool_name": "Shell", "conversation_id": conversation,
                                          "tool_input": {"command": command, "working_directory": str(self.repo)}})

    def draft(self, name: str = "totals") -> str:
        stages = self.repo / ".governance" / "stages"
        stages.mkdir(parents=True, exist_ok=True)
        (stages / f"{name}.json").write_text(json.dumps(CONTRACT), encoding="utf-8")
        return f"{sys.executable} -B {STAGECTL} --repo . freeze --contract .governance/stages/{name}.json --owner-approved"

    def test_owner_typing_approve_lets_the_agent_freeze_that_contract_once(self) -> None:
        command = self.draft()
        self.assertEqual(self.approval_command(command).get("permission"), "deny")
        self.assertEqual(self.approve(), {"continue": True})
        self.assertEqual(self.approval_command(command), {})
        subprocess.run(command, shell=True, cwd=self.repo, check=True, capture_output=True)
        self.assertEqual(self.approval_command(command).get("permission"), "deny")

    def test_only_a_message_that_starts_with_the_command_is_an_approval(self) -> None:
        command = self.draft()
        for text in ("the owner said /approve", "approve", "/approved", ""):
            self.approve(text)
            self.assertEqual(self.approval_command(command).get("permission"), "deny", text)
        self.approve("  /approve looks right")
        self.assertEqual(self.approval_command(command), {})

    def test_an_approval_does_not_carry_to_another_conversation_or_past_its_window(self) -> None:
        command = self.draft()
        self.approve()
        self.assertEqual(self.approval_command(command, conversation="c2").get("permission"), "deny")
        self.assertEqual(self.approval_command(command), {})
        self.approve()
        grant = next((self.repo / ".git" / "governance-v3").rglob("*.approval.json"))
        value = json.loads(grant.read_text())
        value["created"] -= 3600
        grant.write_text(json.dumps(value))
        self.assertIn("expired", self.approval_command(command)["agent_message"])

    def test_a_contract_changed_after_approval_is_not_approved(self) -> None:
        command = self.draft()
        self.approve()
        changed = {**CONTRACT, "intent": "Something the owner never saw."}
        (self.repo / ".governance/stages/totals.json").write_text(json.dumps(changed), encoding="utf-8")
        self.assertIn("changed after", self.approval_command(command)["agent_message"])
        self.assertEqual(self.approval_command(command).get("permission"), "deny")

    def test_an_approval_covers_the_newest_or_named_contract_only(self) -> None:
        older = self.draft("older")
        os.utime(self.repo / ".governance/stages/older.json", (1, 1))
        newer = self.draft("newer")
        self.approve()
        self.assertEqual(self.approval_command(older).get("permission"), "deny")
        self.assertEqual(self.approval_command(newer), {})
        self.approve("/approve older")
        self.assertEqual(self.approval_command(older), {})

    def test_an_approval_cannot_be_spent_on_anything_but_the_plain_command(self) -> None:
        command = self.draft()
        fake = self.repo / "stagectl"
        fake.write_text("print('x')\n", encoding="utf-8")
        for attempt in (command + " && git push", command + " ; rm -rf x", "echo $(" + command + ")",
                        f"{sys.executable} stagectl --repo . freeze --contract .governance/stages/totals.json --owner-approved",
                        command.replace("--repo .", "--repo /tmp"),
                        f"{sys.executable} {PACKAGE / 'scripts' / 'rulekit'} --repo . baseline --owner-approved"):
            self.approve()
            self.assertEqual(self.approval_command(attempt).get("permission"), "deny", attempt)
        self.approve("/approve baseline")
        self.assertEqual(self.approval_command(command).get("permission"), "deny")
        self.approve("/approve baseline")
        self.assertEqual(self.approval_command(
            f"{sys.executable} {PACKAGE / 'scripts' / 'rulekit'} --repo . baseline --owner-approved"), {})

    def test_agent_cannot_record_owner_approval(self) -> None:
        for command in ("python3 scripts/stagectl --repo . freeze --contract stage.json --owner-approved",
                        "stagectl revise --owner-approved --contract s.json --reason 'x'"):
            self.assertEqual(self.shell(command).get("permission"), "deny")

    def test_other_stagectl_commands_are_not_blocked(self) -> None:
        self.assertEqual(self.shell("python3 scripts/stagectl --repo . run-check --all"), {})

    def test_stage_state_cannot_be_touched_directly(self) -> None:
        self.assertEqual(self.shell("rm -rf .git/governance-v3/stages").get("permission"), "deny")
        edit = self.hook("pre-tool-use", {"tool_name": "Write",
                                          "tool_input": {"file_path": ".git/governance-v3/active/x.json"}})
        self.assertEqual(edit.get("permission"), "deny")

    def test_risky_git_is_blocked_only_while_a_stage_is_active(self) -> None:
        self.assertEqual(self.shell("git reset --hard HEAD~1"), {})
        self.freeze()
        self.assertEqual(self.shell("git reset --hard HEAD~1").get("permission"), "deny")
        self.assertEqual(self.shell("git status"), {})
        self.assertEqual(self.shell("git commit -m work"), {})
        self.assertEqual(self.shell("npm test"), {})

    def test_malformed_payload_denies_only_approval_attempts(self) -> None:
        self.assertEqual(self.hook("pre-tool-use", b"{not json"), {})
        self.assertEqual(self.hook("pre-tool-use", b"{not json --owner-approved").get("permission"), "deny")

    def test_stop_is_silent_without_a_stage(self) -> None:
        self.assertEqual(self.hook("stop", {"status": "completed"}), {})

    def test_stop_sends_the_agent_back_while_the_stage_is_unproven(self) -> None:
        self.freeze()
        message = self.hook("stop", {"status": "completed"})["followup_message"]
        self.assertIn("not proven yet", message)
        self.assertIn("CHK-001", message)
        self.assertEqual(self.hook("stop", {"status": "aborted"}), {})

    def test_stop_prompts_closure_once_evidence_is_current_and_goes_quiet_after(self) -> None:
        self.freeze()
        self.stagectl("run-check", "--all")
        self.assertIn("Close it", self.hook("stop", {"status": "completed"})["followup_message"])
        self.stagectl("close")
        self.assertEqual(self.hook("stop", {"status": "completed"}), {})

    # require_stage

    def require_stage(self, exempt: list[str] | None = None) -> None:
        (self.repo / ".governance").mkdir(exist_ok=True)
        (self.repo / ".governance" / "config.json").write_text(
            json.dumps({"version": 1, "require_stage": True, "exempt": exempt or []}), encoding="utf-8")
        git = ["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "adopt"], check=True)

    def edit(self, path: str, tool: str = "Write") -> dict:
        return self.hook("pre-tool-use", {"tool_name": tool, "tool_input": {"file_path": path}})

    def test_planning_documents_need_no_stage_under_the_adoption_defaults(self) -> None:
        spec = importlib.util.spec_from_file_location("adopt", PACKAGE / "scripts" / "adopt.py")
        adopt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adopt)
        self.require_stage(exempt=list(adopt.PLANNING_DOCS))
        for path in ("GLOSSARY.md", "src/billing/GLOSSARY.md", "docs/adr/0001-queue.md", "docs/agents/issue-tracker.md",
                     ".scratch/archive/issues/01-archive.md"):
            self.assertEqual(self.edit(path), {}, path)
        for path in ("src/app.py", "AGENTS.md", "docs/guide.md"):
            self.assertEqual(self.edit(path).get("permission"), "deny", path)

    def test_edits_are_free_in_a_project_that_did_not_opt_in(self) -> None:
        self.assertEqual(self.edit("src/app.py"), {})

    def test_edits_need_a_stage_once_the_project_requires_one(self) -> None:
        self.require_stage(exempt=["docs/**"])
        denied = self.edit("src/app.py")
        self.assertEqual(denied.get("permission"), "deny")
        self.assertIn(".governance/stages/", denied["agent_message"])
        self.assertEqual(self.edit(str(self.repo / "src" / "app.py")).get("permission"), "deny")
        self.assertEqual(self.edit("src/app.py", tool="Read"), {})
        self.assertEqual(self.edit("docs/guide.md"), {})
        self.assertEqual(self.edit(".governance/stages/totals.json"), {})
        self.assertEqual(self.edit(str(self.repo.parent / "elsewhere.txt")), {})
        self.freeze()
        self.assertEqual(self.edit("src/app.py"), {})

    def test_agent_cannot_edit_the_config_or_write_a_receipt(self) -> None:
        self.assertEqual(self.edit(".governance/receipts/ST-x.json").get("permission"), "deny")
        self.require_stage()
        self.freeze()
        self.assertEqual(self.edit(".governance/config.json").get("permission"), "deny")
        self.assertEqual(self.edit(".governance/receipts/ST-x.json").get("permission"), "deny")

    def test_agent_cannot_grow_the_rule_baseline(self) -> None:
        self.assertEqual(self.shell("python tools/governance/rulekit baseline --owner-approved").get("permission"), "deny")
        self.assertEqual(self.shell("python tools/governance/rulekit baseline"), {})

    def test_stop_reports_changes_made_without_a_stage(self) -> None:
        self.require_stage(exempt=["docs/**"])
        self.assertEqual(self.hook("stop", {"status": "completed"}), {})
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "guide.md").write_text("x\n", encoding="utf-8")
        self.assertEqual(self.hook("stop", {"status": "completed"}), {})
        (self.repo / "app.py").write_text("print(1)\n", encoding="utf-8")
        message = self.hook("stop", {"status": "completed"})["followup_message"]
        self.assertIn("app.py", message)
        self.assertNotIn("guide.md", message)

    def test_stop_names_a_changed_file_in_full_and_honours_exemptions_for_the_first_one(self) -> None:
        self.require_stage(exempt=["GLOSSARY.md"])
        (self.repo / "AGENTS.md").write_text("# guide\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "AGENTS.md"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "-q", "-m", "guide"], check=True)
        (self.repo / "AGENTS.md").write_text("# guide\n\nmore\n", encoding="utf-8")
        message = self.hook("stop", {})["followup_message"]
        self.assertIn(" AGENTS.md.", message)
        self.assertNotIn(" GENTS.md", message)
        subprocess.run(["git", "-C", str(self.repo), "checkout", "-q", "AGENTS.md"], check=True)
        (self.repo / "GLOSSARY.md").write_text("# words\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "GLOSSARY.md"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "commit", "-q", "-m", "words"], check=True)
        (self.repo / "GLOSSARY.md").write_text("# words\n\nreport\n", encoding="utf-8")
        self.assertEqual(self.hook("stop", {}), {})

    def test_stop_reports_the_same_unproven_change_once(self) -> None:
        self.require_stage()
        (self.repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.assertIn("followup_message", self.hook("stop", {}))
        self.assertEqual(self.hook("stop", {}), {})
        (self.repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.assertIn("followup_message", self.hook("stop", {}))

    def test_stop_is_quiet_after_a_stage_closed_on_the_current_code(self) -> None:
        self.require_stage()
        (self.repo / "app.py").write_text("print(1)\n", encoding="utf-8")
        self.freeze()
        self.stagectl("run-check", "--all")
        self.stagectl("close")
        self.assertEqual(self.hook("stop", {"status": "completed"}), {})
        (self.repo / "app.py").write_text("print(2)\n", encoding="utf-8")
        self.assertIn("app.py", self.hook("stop", {"status": "completed"})["followup_message"])

    # protected check configuration

    def rules_file(self) -> None:
        (self.repo / ".governance").mkdir(exist_ok=True)
        (self.repo / ".governance" / "rules.json").write_text('{"version": 1, "rules": []}', encoding="utf-8")

    def test_check_configs_are_free_in_a_project_without_rules(self) -> None:
        self.assertEqual(self.edit("ruff.toml"), {})
        self.assertEqual(self.edit("tsconfig.json"), {})

    def test_agent_cannot_loosen_the_checks_without_the_owner_seeing_it(self) -> None:
        self.rules_file()
        for path in ("ruff.toml", "eslint.config.mjs", "tsconfig.json", "tsconfig.build.json", ".governance/rules.json",
                     ".github/workflows/governance.yml", ".governance/baseline.json"):
            self.assertEqual(self.edit(path).get("permission"), "deny", path)
        self.assertEqual(self.edit("src/app.py"), {})
        self.assertEqual(self.edit("packages/web/tsconfig.json"), {})
        self.freeze()
        self.assertIn("outputs", self.edit("ruff.toml")["agent_message"])

    def test_a_check_config_named_in_the_frozen_contract_can_be_edited(self) -> None:
        self.rules_file()
        (self.repo / "ruff.toml").write_text("line-length = 120\n", encoding="utf-8")
        (self.repo / "stage.json").write_text(json.dumps({**CONTRACT, "outputs": ["ruff.toml"]}), encoding="utf-8")
        self.freeze()
        self.assertEqual(self.edit("ruff.toml"), {})
        self.assertEqual(self.edit("eslint.config.mjs").get("permission"), "deny")
        self.assertEqual(self.edit(".governance/baseline.json").get("permission"), "deny")

    def test_owner_can_protect_more_files(self) -> None:
        self.rules_file()
        (self.repo / ".governance" / "config.json").write_text(
            json.dumps({"version": 1, "require_stage": False, "protected": ["pyproject.toml"]}), encoding="utf-8")
        self.assertEqual(self.edit("pyproject.toml").get("permission"), "deny")
        self.assertEqual(self.edit("README.md"), {})


if __name__ == "__main__":
    unittest.main()
