#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


STAGECTL = Path(__file__).resolve().parents[1] / "scripts" / "stagectl"


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
        verdicts = list((self.repo / ".governance" / "verdicts").glob("*.json"))
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(self.ctl("gate")[0], 0)

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

    def test_a_verdict_recorded_on_another_clone_is_accepted_and_a_bad_one_is_not(self) -> None:
        self.write("stage.json", json.dumps(contract(review="independent")))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "contract")
        code, frozen = self.ctl("freeze", "--contract", "stage.json", "--owner-approved")
        self.assertEqual(code, 0, frozen)
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        stage = frozen["stage_id"]
        judged = self.git_out("rev-parse", "HEAD")
        remote = self.repo.parent / (self.repo.name + "-remote.git")
        checker = self.repo.parent / (self.repo.name + "-checker")
        self.addCleanup(shutil.rmtree, remote, True)
        self.addCleanup(shutil.rmtree, checker, True)
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-q", "-u", "origin", "HEAD")
        subprocess.run(["git", "clone", "-q", str(remote), str(checker)], check=True)
        author_common = self.common_dir(self.repo)
        checker_common = self.common_dir(checker)
        self.assertNotEqual(author_common, checker_common)
        self.assertFalse((checker_common / "governance-v3" / "stages" / stage).exists())

        refused = self.verify_at(checker, stage)
        self.assertEqual(refused[0], 2)
        self.assertIn("no local stage state", refused[1]["error"])
        (checker / "app.py").write_text("def total(days, rate):\n    return 0\n", encoding="utf-8")
        dirty = self.verify_at(checker, stage, "--contract", "stage.json", "--checker", "other-vm")
        self.assertEqual(dirty[0], 2)
        self.assertIn("differ from HEAD", dirty[1]["error"])
        subprocess.run(["git", "-C", str(checker), "checkout", "-q", "--", "app.py"], check=True)

        code, recorded = self.verify_at(
            checker, stage, "--contract", "stage.json", "--checker", "other-vm", "--control", "check.py",
            "--live", "totals=1=verified")
        self.assertEqual(code, 0, recorded)
        verdict_path = checker / recorded["verdict"]
        body = json.loads(verdict_path.read_text(encoding="utf-8"))
        self.assertEqual(body["head"]["commit"], judged)
        self.assertEqual(body["checker"]["identity"], "other-vm")
        self.assertEqual(body["report"], "PASS")
        self.assertEqual(body["checked"]["checks"][0]["status"], "passed")
        self.assertEqual(body["evidence"]["control"], "check.py")
        self.assertEqual(body["evidence"]["live"], [{"feature": "totals", "entry": "1", "outcome": "verified"}])
        self.assertEqual(body["record_sha256"], canon({k: v for k, v in body.items() if k != "record_sha256"}))
        self.assertEqual(verdict_path.name, body["record_sha256"] + ".json")

        self.git_at(checker, "add", "-A")
        self.git_at(checker, "commit", "-q", "-m", "verdict")
        self.git_at(checker, "push", "-q")
        self.git("pull", "-q", "--ff-only")
        status = self.ctl("status")[1]
        self.assertNotIn("review-missing", self.codes(status))
        self.assertIn("check-stale", self.codes(status))
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        code, closed = self.ctl("close")
        self.assertEqual(code, 0, closed)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "receipt")
        code, gated = self.ctl("gate")
        self.assertEqual(code, 0, gated)
        self.assertEqual(gated["verdict"], body["record_sha256"])

        original = (self.repo / ".governance" / "verdicts" / verdict_path.name).read_text(encoding="utf-8")
        tampered = json.loads(original)
        tampered["evidence"]["summary"] = "rewritten after the fact without a new hash"
        (self.repo / ".governance" / "verdicts" / verdict_path.name).write_text(json.dumps(tampered), encoding="utf-8")
        self.assertEqual(self.codes(self.ctl("gate")[1]), {"verdict-tampered"})

        shifted = json.loads(original)
        shifted["head"] = {**shifted["head"], "tree": "0" * 40}
        shifted["record_sha256"] = canon({k: v for k, v in shifted.items() if k != "record_sha256"})
        directory = self.repo / ".governance" / "verdicts"
        for path in directory.glob("*.json"):
            path.unlink()
        (directory / f"{shifted['record_sha256']}.json").write_text(json.dumps(shifted), encoding="utf-8")
        self.assertEqual(self.codes(self.ctl("gate")[1]), {"verdict-tree"})

        incomplete = json.loads(original)
        del incomplete["checker"]
        incomplete["record_sha256"] = canon({k: v for k, v in incomplete.items() if k != "record_sha256"})
        for path in directory.glob("*.json"):
            path.unlink()
        (directory / f"{incomplete['record_sha256']}.json").write_text(json.dumps(incomplete), encoding="utf-8")
        self.assertEqual(self.codes(self.ctl("gate")[1]), {"verdict-invalid"})

        for path in directory.glob("*.json"):
            path.unlink()
        self.assertEqual(self.codes(self.ctl("gate")[1]), {"verdict-missing"})

    def test_resume_does_not_reopen_a_closed_stage_without_a_reproof(self) -> None:
        self.freeze()
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        self.assertEqual(self.ctl("close")[0], 0)
        code, out = self.ctl("resume")
        self.assertEqual(code, 2, out)
        self.assertIn("independent", out["error"])

    def test_a_signed_verdict_is_accepted_and_a_bad_signature_is_rejected(self) -> None:
        keys = self.repo.parent / (self.repo.name + "-keys")
        self.addCleanup(shutil.rmtree, keys, True)
        checker_key = self.make_key(keys, "checker")
        alice_key = self.make_key(keys, "alice")
        attacker_key = self.make_key(keys, "attacker")
        self.git("branch", "-M", "main")
        signers = self.signer_line("other-vm", checker_key) + self.signer_line("alice", alice_key)
        self.write(".governance/verdict-signers", signers)
        self.write(".governance/config.json", json.dumps({"require_verdict_signature": True}))
        self.write("stage.json", json.dumps(contract(review="independent")))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "trust the checker")
        self.git("checkout", "-q", "-b", "feature")
        self.write("app.py", "def total(days, rate):\n    if days < 0:\n        raise ValueError('days')\n    return days * rate\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "reject negative days")
        code, frozen = self.ctl("freeze", "--contract", "stage.json", "--owner-approved")
        self.assertEqual(code, 0, frozen)
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        stage = frozen["stage_id"]
        remote = self.repo.parent / (self.repo.name + "-remote.git")
        checker = self.repo.parent / (self.repo.name + "-checker")
        self.addCleanup(shutil.rmtree, remote, True)
        self.addCleanup(shutil.rmtree, checker, True)
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run(["git", "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/feature"], check=True)
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-q", "-u", "origin", "main")
        self.git("push", "-q", "-u", "origin", "feature")
        subprocess.run(["git", "clone", "-q", str(remote), str(checker)], check=True)
        self.assertNotEqual(self.common_dir(self.repo), self.common_dir(checker))

        missing_key = self.verify_at(checker, stage, "--contract", "stage.json", "--checker", "other-vm")
        self.assertEqual(missing_key[0], 2, missing_key[1])
        self.assertIn("signed verdict", missing_key[1]["error"])
        code, recorded = self.verify_at(
            checker, stage, "--contract", "stage.json", "--checker", "other-vm", "--key", str(checker_key))
        self.assertEqual(code, 0, recorded)
        self.assertTrue(recorded["signed"])
        body = json.loads((checker / recorded["verdict"]).read_text(encoding="utf-8"))
        self.assertNotIn("signature", body)
        self.assertEqual(body["checker"]["identity"], "other-vm")
        sig = checker / ".governance" / "verdicts" / f"{body['record_sha256']}.sig"
        self.assertIn(b"BEGIN SSH SIGNATURE", sig.read_bytes())
        self.git_at(checker, "add", "-A")
        self.git_at(checker, "commit", "-q", "-m", "signed verdict")
        self.git_at(checker, "push", "-q")
        self.git("pull", "-q", "--ff-only")
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        self.assertEqual(self.ctl("close")[0], 0)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "receipt")
        self.git("push", "-q")
        self.assertEqual(self.ctl("gate", "--base", "main")[0], 0)
        proven = self.git_out("rev-parse", "HEAD")
        verdict_path = self.repo / ".governance" / "verdicts" / f"{body['record_sha256']}.json"
        sig_path = verdict_path.with_suffix(".sig")
        honest_json = verdict_path.read_text(encoding="utf-8")
        honest_sig = sig_path.read_bytes()

        sig_path.unlink()
        self.assertEqual(self.codes(self.ctl("gate", "--base", "main")[1]), {"verdict-unsigned"})
        sig_path.write_bytes(honest_sig)

        tampered = json.loads(honest_json)
        tampered["evidence"]["summary"] = "changed after the signature was made"
        tampered["record_sha256"] = canon({k: v for k, v in tampered.items() if k != "record_sha256"})
        forged = verdict_path.parent / f"{tampered['record_sha256']}.json"
        verdict_path.unlink()
        forged.write_text(json.dumps(tampered), encoding="utf-8")
        forged.with_suffix(".sig").write_bytes(honest_sig)
        self.assertIn("verdict-signature", self.codes(self.ctl("gate", "--base", "main")[1]))
        forged.unlink()
        forged.with_suffix(".sig").unlink()
        verdict_path.write_text(honest_json, encoding="utf-8")
        sig_path.write_bytes(honest_sig)

        self.sign_hash(attacker_key, body["record_sha256"], sig_path)
        self.assertIn("verdict-untrusted", self.codes(self.ctl("gate", "--base", "main")[1]))
        self.sign_hash(alice_key, body["record_sha256"], sig_path)
        self.assertIn("verdict-identity", self.codes(self.ctl("gate", "--base", "main")[1]))
        sig_path.write_bytes(honest_sig)
        self.assertEqual(self.ctl("gate", "--base", "main")[0], 0)

        self.write(".governance/verdict-signers", signers + self.signer_line("other-vm", attacker_key))
        self.sign_hash(attacker_key, body["record_sha256"], sig_path)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "trust a key added on this branch")
        self.assertIn("verdict-untrusted", self.codes(self.ctl("gate", "--base", "main")[1]))
        self.git("reset", "-q", "--hard", proven)

        self.write(".governance/config.json", json.dumps({"require_verdict_signature": False}))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "turn signing off")
        self.git("push", "-q")
        self.git_at(checker, "fetch", "-q", "origin")
        self.git_at(checker, "reset", "-q", "--hard", "origin/feature")
        code, resigned = self.verify_at(
            checker, stage, "--contract", "stage.json", "--checker", "other-vm", "--key", str(checker_key))
        self.assertEqual(code, 0, resigned)
        self.git_at(checker, "add", "-A")
        self.git_at(checker, "commit", "-q", "-m", "signed despite the flag")
        self.git_at(checker, "push", "-q")
        self.git("pull", "-q", "--ff-only")
        fresh = json.loads((self.repo / ".governance" / "verdicts" / Path(resigned["verdict"]).name).read_text(encoding="utf-8"))
        receipt_path = self.repo / ".governance" / "receipts" / f"{stage}.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["tree"] = fresh["head"]["tree"]
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        self.assertEqual(self.ctl("gate", "--base", "main")[0], 0)
        fresh_sig = self.repo / ".governance" / "verdicts" / f"{fresh['record_sha256']}.sig"
        fresh_sig.unlink()
        self.assertIn("verdict-unsigned", self.codes(self.ctl("gate", "--base", "main")[1]))
        self.git("reset", "-q", "--hard", proven)

        self.git("checkout", "-q", "main")
        self.write("notes.md", "a note on main\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "notes")
        self.git("push", "-q")
        self.git("checkout", "-q", "feature")
        self.git("rebase", "main")
        self.git("push", "-q", "--force-with-lease")
        self.git_at(checker, "fetch", "-q", "origin")
        self.git_at(checker, "reset", "-q", "--hard", "origin/feature")
        code, again = self.reprove_at(
            checker, stage, body["record_sha256"], "origin/main", "--checker", "other-vm", "--key", str(checker_key))
        self.assertEqual(code, 0, again)
        self.assertTrue(again["signed"])
        second = json.loads((checker / again["verdict"]).read_text(encoding="utf-8"))
        self.assertEqual(second["supersedes"]["record_sha256"], body["record_sha256"])
        self.assertNotEqual(second["record_sha256"], body["record_sha256"])
        second_sig = checker / ".governance" / "verdicts" / f"{second['record_sha256']}.sig"
        self.assertTrue(second_sig.is_file())
        self.assertNotEqual(second_sig.read_bytes(), honest_sig)
        self.git_at(checker, "add", "-A")
        self.git_at(checker, "commit", "-q", "-m", "signed reproof")
        self.git_at(checker, "push", "-q")
        self.git("pull", "-q", "--ff-only")
        code, resumed = self.ctl("resume")
        self.assertEqual(code, 0, resumed)
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        self.assertEqual(self.ctl("close")[0], 0)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "rebased receipt")
        self.assertEqual(self.ctl("gate", "--base", "main")[0], 0)
        self.assertEqual(self.ctl("gate", "--base", "main")[1]["verdict"], second["record_sha256"])

    def test_rebase_reproof_records_a_fresh_verdict_and_rejects_a_changed_or_failed_run(self) -> None:
        self.git("branch", "-M", "main")
        self.write("flag.txt", "ok\n")
        self.write("check.py", "import app, pathlib, sys\n"
                   "text = pathlib.Path('flag.txt').read_text(encoding='utf-8').strip()\n"
                   "sys.exit(0 if text == 'ok' and app.total(3, 10) == 30 else 1)\n")
        self.write("stage.json", json.dumps(contract(review="independent")))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "contract")
        self.git("checkout", "-q", "-b", "feature")
        self.write("app.py", "def total(days, rate):\n    if days < 0:\n        raise ValueError('days')\n    return days * rate\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "reject negative days")
        code, frozen = self.ctl("freeze", "--contract", "stage.json", "--owner-approved")
        self.assertEqual(code, 0, frozen)
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        stage = frozen["stage_id"]
        remote = self.repo.parent / (self.repo.name + "-remote.git")
        checker = self.repo.parent / (self.repo.name + "-checker")
        self.addCleanup(shutil.rmtree, remote, True)
        self.addCleanup(shutil.rmtree, checker, True)
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run(["git", "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/feature"], check=True)
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-q", "-u", "origin", "main")
        self.git("push", "-q", "-u", "origin", "feature")
        subprocess.run(["git", "clone", "-q", str(remote), str(checker)], check=True)
        self.assertNotEqual(self.common_dir(self.repo), self.common_dir(checker))
        self.assertFalse((self.common_dir(checker) / "governance-v3" / "stages" / stage).exists())

        code, recorded = self.verify_at(
            checker, stage, "--contract", "stage.json", "--checker", "other-vm", "--control", "check.py",
            "--live", "totals=1=verified")
        self.assertEqual(code, 0, recorded)
        first = json.loads((checker / recorded["verdict"]).read_text(encoding="utf-8"))
        self.git_at(checker, "add", "-A")
        self.git_at(checker, "commit", "-q", "-m", "verdict")
        self.git_at(checker, "push", "-q")
        self.git("pull", "-q", "--ff-only")
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        self.assertEqual(self.ctl("close")[0], 0)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "receipt")
        self.git("push", "-q")
        self.assertEqual(self.ctl("gate", "--base", "main")[0], 0)

        self.git("checkout", "-q", "main")
        self.write("notes.md", "a note on main\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "notes")
        self.git("push", "-q")
        self.git("checkout", "-q", "feature")
        self.git("rebase", "main")
        self.git("push", "-q", "--force-with-lease")
        code, blocked = self.ctl("gate", "--base", "main")
        self.assertNotEqual(code, 0, blocked)
        self.assertEqual(self.codes(blocked), {"no-receipt"})
        new_tree = blocked["tree"]
        self.assertNotEqual(new_tree, first["head"]["tree"])
        receipt_path = self.repo / ".governance" / "receipts" / f"{stage}.json"
        original_receipt = receipt_path.read_text(encoding="utf-8")
        shifted = json.loads(original_receipt)
        shifted["tree"] = new_tree
        receipt_path.write_text(json.dumps(shifted), encoding="utf-8")
        self.assertEqual(self.codes(self.ctl("gate", "--base", "main")[1]), {"verdict-tree"})
        receipt_path.write_text(original_receipt, encoding="utf-8")

        refused = self.reprove_at(self.repo, stage, first["record_sha256"], "main")
        self.assertEqual(refused[0], 2, refused[1])
        self.assertIn("local state", refused[1]["error"])
        early = self.ctl("resume")
        self.assertEqual(early[0], 2, early[1])

        self.git_at(checker, "fetch", "-q", "origin")
        self.git_at(checker, "reset", "-q", "--hard", "origin/feature")
        verdicts = checker / ".governance" / "verdicts"
        before = sorted(path.name for path in verdicts.glob("*.json"))
        (checker / "app.py").write_text(
            "def total(days, rate):\n    if days < 0:\n        raise ValueError('days')\n    return days * rate  # extra\n",
            encoding="utf-8")
        self.git_at(checker, "add", "-A")
        self.git_at(checker, "commit", "-q", "-m", "change the patch")
        changed = self.reprove_at(checker, stage, first["record_sha256"], "origin/main", "--checker", "other-vm")
        self.assertEqual(changed[0], 2, changed[1])
        self.assertIn("patch changed", changed[1]["error"])
        self.assertEqual(sorted(path.name for path in verdicts.glob("*.json")), before)
        self.git_at(checker, "reset", "-q", "--hard", "origin/feature")

        code, again = self.reprove_at(
            checker, stage, first["record_sha256"], "origin/main", "--checker", "other-vm",
            "--control", "check.py", "--live", "totals=1=verified")
        self.assertEqual(code, 0, again)
        second_path = checker / again["verdict"]
        second = json.loads(second_path.read_text(encoding="utf-8"))
        self.assertNotEqual(second["record_sha256"], first["record_sha256"])
        self.assertEqual(second["head"]["tree"], again["tree"])
        self.assertNotEqual(second["head"]["tree"], first["head"]["tree"])
        self.assertEqual(second["head"]["commit"], again["commit"])
        self.assertNotEqual(second["head"]["commit"], first["head"]["commit"])
        self.assertEqual(second["supersedes"]["record_sha256"], first["record_sha256"])
        self.assertEqual(second["supersedes"]["commit"], first["head"]["commit"])
        self.assertEqual(second["supersedes"]["tree"], first["head"]["tree"])
        self.assertEqual(second["patch_id"], second["supersedes"]["patch_id"])
        self.assertEqual(second["checked"]["checks"][0]["status"], "passed")
        self.assertEqual(second["checker"]["identity"], "other-vm")
        self.assertEqual(second["record_sha256"], canon({k: v for k, v in second.items() if k != "record_sha256"}))
        self.git_at(checker, "add", "-A")
        self.git_at(checker, "commit", "-q", "-m", "reproof")
        self.git_at(checker, "push", "-q")
        self.git("pull", "-q", "--ff-only")
        code, resumed = self.ctl("resume")
        self.assertEqual(code, 0, resumed)
        self.assertEqual(resumed["stage_id"], stage)
        self.assertEqual(self.ctl("run-check", "--all")[0], 0)
        code, closed = self.ctl("close")
        self.assertEqual(code, 0, closed)
        self.assertNotEqual(closed["receipt"], f".governance/receipts/{stage}.json")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "rebased receipt")
        self.git("push", "-q")
        code, gated = self.ctl("gate", "--base", "main")
        self.assertEqual(code, 0, gated)
        self.assertEqual(gated["verdict"], second["record_sha256"])
        kept = self.repo / ".governance" / "verdicts" / f"{first['record_sha256']}.json"
        fresh = self.repo / ".governance" / "verdicts" / f"{second['record_sha256']}.json"
        self.assertTrue(kept.is_file())
        honest = fresh.read_text(encoding="utf-8")

        fresh.unlink()
        self.assertIn("verdict-tree", self.codes(self.ctl("gate", "--base", "main")[1]))
        fresh.write_text(honest, encoding="utf-8")
        self.assertEqual(self.ctl("gate", "--base", "main")[0], 0)

        tampered = json.loads(honest)
        tampered["evidence"]["summary"] = "rewritten after the fact without a new hash"
        fresh.write_text(json.dumps(tampered), encoding="utf-8")
        self.assertIn("verdict-tampered", self.codes(self.ctl("gate", "--base", "main")[1]))
        fresh.write_text(honest, encoding="utf-8")

        forged = json.loads(honest)
        forged["supersedes"] = {**forged["supersedes"], "patch_id": "ab" * 20}
        forged["record_sha256"] = canon({k: v for k, v in forged.items() if k != "record_sha256"})
        fresh.unlink()
        forged_path = fresh.parent / f"{forged['record_sha256']}.json"
        forged_path.write_text(json.dumps(forged), encoding="utf-8")
        self.assertIn("verdict-supersedes", self.codes(self.ctl("gate", "--base", "main")[1]))
        forged_path.unlink()
        fresh.write_text(honest, encoding="utf-8")
        self.git("checkout", "-q", "--", ".")

        self.git("checkout", "-q", "main")
        self.write("flag.txt", "no\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "flag off")
        self.git("push", "-q")
        self.git("checkout", "-q", "feature")
        self.git("rebase", "main")
        self.git("push", "-q", "--force-with-lease")
        self.git_at(checker, "fetch", "-q", "origin")
        self.git_at(checker, "reset", "-q", "--hard", "origin/feature")
        failed = self.reprove_at(
            checker, stage, second["record_sha256"], "origin/main", "--checker", "other-vm")
        self.assertEqual(failed[0], 3, failed[1])
        self.assertEqual(failed[1]["outcome"], "fail")
        failed_body = json.loads((checker / failed[1]["verdict"]).read_text(encoding="utf-8"))
        self.assertEqual(failed_body["checked"]["checks"][0]["status"], "failed")
        self.assertNotEqual(failed_body["record_sha256"], second["record_sha256"])
        self.assertEqual(failed_body["supersedes"]["record_sha256"], second["record_sha256"])
        self.assertEqual(failed_body["patch_id"], failed_body["supersedes"]["patch_id"])
        self.git_at(checker, "add", "-A")
        self.git_at(checker, "commit", "-q", "-m", "failed reproof")
        self.git_at(checker, "push", "-q")
        self.git("pull", "-q", "--ff-only")
        code, blocked = self.ctl("gate", "--base", "main")
        self.assertEqual(self.codes(blocked), {"no-receipt"})
        newest = blocked["tree"]
        cover = self.repo / ".governance" / "receipts" / f"{stage}-cover.json"
        cover.write_text(json.dumps({"version": 1, "stage_id": stage, "review": "independent", "tree": newest,
                                     "checks": []}), encoding="utf-8")
        blocked = self.ctl("gate", "--base", "main")[1]
        self.assertIn("verdict-failed", self.codes(blocked))
        self.assertFalse(blocked["passed"])

    def git_out(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True).stdout.strip()

    def git_at(self, repo: Path, *args: str) -> None:
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                       check=True, capture_output=True)

    def common_dir(self, repo: Path) -> Path:
        raw = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-common-dir"],
                             check=True, capture_output=True, text=True).stdout.strip()
        path = Path(raw)
        return path if path.is_absolute() else (repo / path).resolve()

    def verify_at(self, repo: Path, stage: str, *extra: str) -> tuple[int, dict]:
        result = subprocess.run(
            [sys.executable, "-B", str(STAGECTL), "--repo", str(repo), "--json", "verify", "--stage", stage,
             "--outcome", "pass", "--summary", "Drove totals through the CLI and saw thirty", *extra],
            capture_output=True, text=True, check=False)
        return result.returncode, json.loads(result.stdout)

    def reprove_at(self, repo: Path, stage: str, supersedes: str, base: str, *extra: str) -> tuple[int, dict]:
        result = subprocess.run(
            [sys.executable, "-B", str(STAGECTL), "--repo", str(repo), "--json", "reprove", "--stage", stage,
             "--supersedes", supersedes, "--base", base, "--contract", "stage.json", "--outcome", "pass",
             "--summary", "Re-ran totals on the rebased tree and saw thirty", *extra],
            capture_output=True, text=True, check=False)
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {"error": result.stderr or result.stdout}
        return result.returncode, payload

    def make_key(self, directory: Path, name: str) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(path), "-N", "", "-q"], check=True)
        return path

    def signer_line(self, principal: str, private_key: Path) -> str:
        kind, material, *_rest = (private_key.with_suffix(".pub")).read_text(encoding="utf-8").split()
        return f'{principal} namespaces="governance-verdict" {kind} {material}\n'

    def sign_hash(self, key: Path, record: str, dest: Path) -> None:
        message = f"governance-verdict-v1 {record}\n".encode()
        with tempfile.TemporaryDirectory() as tmp:
            payload = Path(tmp) / "verdict"
            payload.write_bytes(message)
            subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "governance-verdict", str(payload)],
                           check=True, capture_output=True)
            dest.write_bytes(payload.with_suffix(".sig").read_bytes())


if __name__ == "__main__":
    unittest.main()
