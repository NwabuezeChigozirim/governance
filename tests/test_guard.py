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


if __name__ == "__main__":
    unittest.main()
