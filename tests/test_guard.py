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

    def test_stop_is_quiet_after_a_stage_closed_on_the_current_code(self) -> None:
        self.require_stage()
        (self.repo / "app.py").write_text("print(1)\n", encoding="utf-8")
        self.freeze()
        self.stagectl("run-check", "--all")
        self.stagectl("close")
        self.assertEqual(self.hook("stop", {"status": "completed"}), {})
        (self.repo / "app.py").write_text("print(2)\n", encoding="utf-8")
        self.assertIn("app.py", self.hook("stop", {"status": "completed"})["followup_message"])


if __name__ == "__main__":
    unittest.main()
