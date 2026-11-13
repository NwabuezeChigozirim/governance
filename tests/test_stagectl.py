#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


STAGECTL = Path(__file__).resolve().parents[1] / "scripts" / "stagectl"


def contract(**changes) -> dict:
    value = {
        "version": 1,
        "name": "Totals slice",
        "intent": "Booking totals multiply days by the daily rate and reject negative days.",
        "review": "none",
        "inputs": ["spec.md"],
        "outputs": ["app.py"],
        "acceptance": [{"id": "AC-001", "description": "The total for three days at ten is thirty", "checks": ["CHK-001"]}],
        "checks": [{"id": "CHK-001", "argv": [sys.executable, "check.py"], "timeout_seconds": 30}],
    }
    value.update(changes)
    return value


class StagectlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.write("spec.md", "Totals are days times rate.\n")
        self.write("app.py", "def total(days, rate):\n    return days * rate\n")
        self.write("check.py", "import app, sys\nsys.exit(0 if app.total(3, 10) == 30 else 1)\n")
        self.write(".gitignore", ".verify/\n__pycache__/\n")
        self.write("stage.json", json.dumps(contract()))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")

    def write(self, name: str, text: str) -> None:
        (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / name).write_text(text, encoding="utf-8")

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                       check=True, capture_output=True)

    def ctl(self, *args: str) -> tuple[int, dict]:
        result = subprocess.run([sys.executable, "-B", str(STAGECTL), "--repo", str(self.repo), "--json", *args],
                                capture_output=True, text=True, check=False)
        return result.returncode, json.loads(result.stdout)

    def freeze(self) -> None:
        code, out = self.ctl("freeze", "--contract", "stage.json", "--owner-approved")
        self.assertEqual(code, 0, out)

    def codes(self, out: dict) -> set[str]:
        return {p["code"] for p in out["problems"]}

    def test_freeze_needs_owner_approval(self) -> None:
        code, out = self.ctl("freeze", "--contract", "stage.json")
        self.assertEqual(code, 4)
        self.assertIn("--owner-approved", out["error"])

    def test_malformed_contracts_are_refused(self) -> None:
        for bad in (contract(intent="todo"), contract(checks=[]), contract(review="self"),
                    contract(checks=[{"id": "CHK-001", "argv": "pytest", "timeout_seconds": 30}]),
                    contract(acceptance=[{"id": "AC-001", "description": "The total is thirty for three days", "checks": ["CHK-009"]}])):
            self.write("stage.json", json.dumps(bad))
            self.assertEqual(self.ctl("freeze", "--contract", "stage.json", "--owner-approved")[0], 2)

    def test_happy_path_closes_without_owner_signoff(self) -> None:
        self.freeze()
        self.assertEqual(self.ctl("status")[0], 3)
        code, out = self.ctl("run-check", "--all")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ctl("status")[0], 0)
        code, out = self.ctl("close")
        self.assertEqual(code, 0, out)
        self.assertTrue((self.repo / out["receipt"]).is_file())
        self.assertEqual(self.ctl("status")[0], 2)

    def test_repeated_identical_freeze_is_a_no_op_and_a_different_one_is_refused(self) -> None:
        self.freeze()
        self.assertFalse(self.ctl("freeze", "--contract", "stage.json", "--owner-approved")[1]["changed"])
        self.write("other.json", json.dumps(contract(name="Other slice")))
        self.assertEqual(self.ctl("freeze", "--contract", "other.json", "--owner-approved")[0], 2)

    def test_close_is_refused_before_checks_run(self) -> None:
        self.freeze()
        code, out = self.ctl("close")
        self.assertEqual(code, 3)
        self.assertEqual(self.codes(out), {"check-missing"})

    def test_failing_check_blocks_closure(self) -> None:
        self.write("app.py", "def total(days, rate):\n    return days + rate\n")
        self.freeze()
        self.assertEqual(self.ctl("run-check", "--id", "CHK-001")[0], 3)
        code, out = self.ctl("close")
        self.assertEqual(code, 3)
        self.assertIn("check-failed", self.codes(out))

    def test_code_change_after_a_pass_makes_the_receipt_stale(self) -> None:
        self.freeze()
        self.ctl("run-check", "--all")
        self.write("app.py", "def total(days, rate):\n    return rate * days\n")
        code, out = self.ctl("close")
        self.assertEqual(code, 3)
        self.assertIn("check-stale", self.codes(out))
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        self.assertEqual(self.ctl("close")[0], 0)

    def test_changed_frozen_input_blocks_until_revised(self) -> None:
        self.freeze()
        self.write("spec.md", "Totals are days times rate, plus tax.\n")
        self.ctl("run-check", "--all")
        code, out = self.ctl("close")
        self.assertEqual(code, 3)
        self.assertIn("input-changed", self.codes(out))
        self.assertEqual(self.ctl("revise", "--contract", "stage.json", "--reason", "Spec now includes tax")[0], 4)
        code, out = self.ctl("revise", "--contract", "stage.json", "--owner-approved", "--reason", "Spec now includes tax")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.codes(self.ctl("status")[1]), {"check-missing"})
        self.ctl("run-check", "--all")
        self.assertEqual(self.ctl("close")[0], 0)

    def test_missing_output_blocks_closure(self) -> None:
        self.write("stage.json", json.dumps(contract(outputs=["app.py", "report.txt"])))
        self.freeze()
        self.ctl("run-check", "--all")
        self.assertIn("output-missing", self.codes(self.ctl("close")[1]))

    def test_check_that_edits_the_code_cannot_certify_it(self) -> None:
        self.write("check.py", "open('app.py', 'a').write('# touched\\n')\n")
        self.freeze()
        code, out = self.ctl("run-check", "--all")
        self.assertEqual(code, 3)
        self.assertEqual(out["results"][0]["status"], "changed-subject")

    def test_timeout_does_not_pass(self) -> None:
        self.write("check.py", "import time\ntime.sleep(30)\n")
        self.write("stage.json", json.dumps(contract(
            checks=[{"id": "CHK-001", "argv": [sys.executable, "check.py"], "timeout_seconds": 1}])))
        self.freeze()
        self.assertEqual(self.ctl("run-check", "--all")[1]["results"][0]["status"], "timed-out")

    def test_altered_log_is_detected(self) -> None:
        self.freeze()
        _, out = self.ctl("run-check", "--all")
        Path(out["results"][0]["log"]).write_text("forged\n", encoding="utf-8")
        self.assertIn("evidence-corrupt", self.codes(self.ctl("close")[1]))

    def test_cancel_abandons_without_completing(self) -> None:
        self.freeze()
        code, out = self.ctl("cancel", "--reason", "The slice was dropped from this wave")
        self.assertEqual(code, 0)
        self.assertFalse(out["completed"])
        self.assertEqual(self.ctl("status")[0], 2)

    # independent verdict

    def reviewed_stage(self) -> tuple[str, Path]:
        self.write("stage.json", json.dumps(contract(review="independent")))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "contract")
        code, out = self.ctl("freeze", "--contract", "stage.json", "--owner-approved")
        self.assertEqual(code, 0, out)
        other = self.repo.parent / (self.repo.name + "-verifier")
        self.addCleanup(shutil.rmtree, other, True)
        self.git("worktree", "add", "-q", "--detach", str(other), "HEAD")
        return out["stage_id"], other

    def verify(self, where: Path, stage: str, outcome: str = "pass") -> tuple[int, dict]:
        result = subprocess.run(
            [sys.executable, "-B", str(STAGECTL), "--repo", str(where), "--json", "verify", "--stage", stage,
             "--outcome", outcome, "--summary", "Drove totals through the CLI and saw thirty"],
            capture_output=True, text=True, check=False)
        return result.returncode, json.loads(result.stdout)

    def test_independent_stage_cannot_close_without_a_verdict(self) -> None:
        self.reviewed_stage()
        self.ctl("run-check", "--all")
        code, out = self.ctl("close")
        self.assertEqual(code, 3)
        self.assertEqual(self.codes(out), {"review-missing"})

    def test_author_worktree_cannot_issue_its_own_verdict(self) -> None:
        stage, _ = self.reviewed_stage()
        code, out = self.verify(self.repo, stage)
        self.assertEqual(code, 2)
        self.assertIn("different worktree", out["error"])

    def test_passing_verdict_from_another_worktree_allows_closure(self) -> None:
        stage, other = self.reviewed_stage()
        self.ctl("run-check", "--all")
        code, out = self.verify(other, stage)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ctl("close")[0], 0)

    def test_verifier_must_hold_the_authors_exact_code(self) -> None:
        stage, other = self.reviewed_stage()
        self.write("app.py", "def total(days, rate):\n    return rate * days\n")
        code, out = self.verify(other, stage)
        self.assertEqual(code, 2)
        self.assertIn("exact code", out["error"])

    def test_declared_fail_and_failing_rerun_both_block(self) -> None:
        stage, other = self.reviewed_stage()
        self.ctl("run-check", "--all")
        self.assertEqual(self.verify(other, stage, "fail")[0], 3)
        self.assertIn("review-failed", self.codes(self.ctl("close")[1]))

    def test_verdict_goes_stale_when_the_code_changes(self) -> None:
        stage, other = self.reviewed_stage()
        self.assertEqual(self.verify(other, stage)[0], 0)
        self.write("app.py", "def total(days, rate):\n    return rate * days\n")
        self.ctl("run-check", "--all")
        self.assertEqual(self.codes(self.ctl("close")[1]), {"review-stale"})

    def test_verifier_rerun_catches_what_passes_only_in_the_authors_tree(self) -> None:
        # The check depends on a Git-ignored file that exists only in the author's worktree.
        self.write("check.py", "import os, sys\nsys.exit(0 if os.path.exists('.verify/local-only') else 1)\n")
        stage, other = self.reviewed_stage()
        (self.repo / ".verify").mkdir()
        (self.repo / ".verify" / "local-only").write_text("x", encoding="utf-8")
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        code, out = self.verify(other, stage)
        self.assertEqual(code, 3)
        self.assertEqual(out["outcome"], "fail")

    def test_each_worktree_has_its_own_stage(self) -> None:
        self.freeze()
        other = self.repo.parent / (self.repo.name + "-wt")
        self.addCleanup(shutil.rmtree, other, True)
        self.git("worktree", "add", "-q", str(other), "-b", "slice-2")
        result = subprocess.run([sys.executable, "-B", str(STAGECTL), "--repo", str(other), "--json", "status"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        result = subprocess.run([sys.executable, "-B", str(STAGECTL), "--repo", str(other), "--json", "freeze",
                                 "--contract", "stage.json", "--owner-approved"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)

    # receipt and merge gate

    def proven(self) -> dict:
        self.freeze()
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        code, out = self.ctl("close")
        self.assertEqual(code, 0, out)
        return json.loads((self.repo / out["receipt"]).read_text(encoding="utf-8"))

    def test_receipt_records_what_was_proven(self) -> None:
        receipt = self.proven()
        self.assertEqual(receipt["intent"], contract()["intent"])
        self.assertEqual([c["id"] for c in receipt["checks"]], ["CHK-001"])
        self.assertEqual(receipt["acceptance"][0]["id"], "AC-001")
        self.assertIsNone(receipt["verdict"])

    def test_gate_passes_once_the_receipt_is_committed_and_fails_after_a_later_edit(self) -> None:
        self.assertEqual(self.ctl("gate")[0], 3)
        self.proven()
        self.assertEqual(self.ctl("gate")[0], 0)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "proven")
        code, out = self.ctl("gate")
        self.assertEqual(code, 0, out)
        self.write("app.py", "def total(days, rate):\n    return days * rate * 1\n")
        code, out = self.ctl("gate")
        self.assertEqual(code, 3)
        self.assertEqual(self.codes(out), {"no-receipt"})

    def test_gate_ignores_python_caches_left_by_running_the_code(self) -> None:
        self.proven()
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "proven")
        self.write("tools/governance/__pycache__/verifyctlcpython-312.pyc", "cache")
        self.write("app/__pycache__/main.cpython-312.pyc", "cache")
        self.write("legacy.pyc", "cache")
        code, out = self.ctl("gate")
        self.assertEqual(code, 0, out)

    def test_the_tools_leave_no_cache_files_behind(self) -> None:
        tools = self.repo / "tools" / "governance"
        tools.mkdir(parents=True)
        for name in ("stagectl", "verifyctl"):
            shutil.copy2(STAGECTL.with_name(name), tools / name)
        result = subprocess.run([sys.executable, str(tools / "stagectl"), "--repo", str(self.repo), "--json", "gate"],
                                capture_output=True, text=True, check=False)
        self.assertIn(result.returncode, (0, 3), result.stderr)
        self.assertFalse((tools / "__pycache__").exists())

    def test_gate_rerun_catches_a_receipt_whose_checks_do_not_pass_here(self) -> None:
        receipt = self.proven()
        self.assertEqual(self.ctl("gate", "--rerun")[0], 0)
        forged = {**receipt, "stage_id": "ST-" + "0" * 32,
                  "checks": [{"id": "CHK-001", "argv": [sys.executable, "-c", "raise SystemExit(1)"], "timeout_seconds": 30}]}
        (self.repo / ".governance/receipts" / f"{receipt['stage_id']}.json").unlink()
        (self.repo / ".governance/receipts" / "ST-forged.json").write_text(json.dumps(forged), encoding="utf-8")
        self.assertEqual(self.ctl("gate")[0], 0)
        code, out = self.ctl("gate", "--rerun")
        self.assertEqual(code, 3)
        self.assertEqual(self.codes(out), {"check-failed"})

    def test_gate_passes_a_change_that_touches_only_exempt_files(self) -> None:
        self.write(".governance/config.json", json.dumps({"version": 1, "require_stage": True, "exempt": ["docs/**"]}))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "config")
        self.write("docs/guide.md", "How totals work.\n")
        self.assertEqual(self.ctl("gate")[0], 3)
        code, out = self.ctl("gate", "--base", "HEAD")
        self.assertEqual(code, 0, out)
        self.assertIn("no governed file", out["reason"])
        self.write("app.py", "def total(days, rate):\n    return 0\n")
        self.assertEqual(self.ctl("gate", "--base", "HEAD")[0], 3)

    def test_gate_writes_the_receipt_as_markdown(self) -> None:
        self.proven()
        target = self.repo / ".verify" / "summary.md"
        target.parent.mkdir()
        self.assertEqual(self.ctl("gate", "--markdown", str(target))[0], 0)
        text = target.read_text(encoding="utf-8")
        self.assertIn(contract()["intent"], text)
        self.assertIn("AC-001", text)

    def test_gate_does_not_touch_the_real_index(self) -> None:
        self.write("app.py", "def total(days, rate):\n    return days * rate  \n")
        before = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"], capture_output=True, text=True).stdout
        self.ctl("gate")
        after = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"], capture_output=True, text=True).stdout
        self.assertEqual(before, after)

    def test_invalid_config_is_refused(self) -> None:
        self.write(".governance/config.json", json.dumps({"require_stage": "yes"}))
        self.assertEqual(self.ctl("gate")[0], 2)


if __name__ == "__main__":
    unittest.main()
