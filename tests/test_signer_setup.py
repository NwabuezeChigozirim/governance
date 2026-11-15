"""The governance-ci signer line and the one-time setup decision."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STAGECTL = ROOT / "scripts" / "stagectl"
WORKFLOW = ROOT / ".github" / "workflows" / "signer-setup.yml"
LINE = 'governance-ci namespaces="governance-verdict" ssh-ed25519 ' + ("A" * 48) + "\n"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(STAGECTL), "--repo", str(ROOT), *args],
        capture_output=True, text=True, check=False)


class SignerLine(unittest.TestCase):
    def test_an_ed25519_public_key_becomes_the_governance_ci_line(self) -> None:
        directory = Path(tempfile.mkdtemp(prefix="signer-line-"))
        private = directory / "verdict-key"
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(private), "-N", "", "-q", "-C", "governance-ci"],
                       check=True)
        result = run("signer-line", "--public-key", str(private.with_suffix(".pub")))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('governance-ci namespaces="governance-verdict" ssh-ed25519 '))
        self.assertTrue(result.stdout.endswith("\n"))
        self.assertNotIn("PRIVATE", result.stdout)
        self.assertNotIn(private.read_text(encoding="utf-8"), result.stdout)
        material = result.stdout.split()[3]
        self.assertNotIn(material, private.read_text(encoding="utf-8"))

    def test_anything_other_than_ed25519_is_refused(self) -> None:
        directory = Path(tempfile.mkdtemp(prefix="signer-line-bad-"))
        path = directory / "key.pub"
        path.write_text("ssh-rsa AAAA comment\n", encoding="utf-8")
        result = run("--json", "signer-line", "--public-key", str(path))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("ssh-ed25519", result.stdout)


class SignerSetupPlan(unittest.TestCase):
    def plan(self, present: bool, text: str | None) -> subprocess.CompletedProcess[str]:
        directory = Path(tempfile.mkdtemp(prefix="signer-plan-"))
        args = ["--json", "signer-setup-plan", "--secret-present" if present else "--secret-absent"]
        if text is not None:
            path = directory / "verdict-signers"
            path.write_text(text, encoding="utf-8")
            args.extend(["--signers", str(path)])
        return run(*args)

    def test_neither_half_means_create(self) -> None:
        result = self.plan(False, None)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('"action": "create"', result.stdout)

    def test_both_halves_are_a_noop(self) -> None:
        result = self.plan(True, "# kept\n\n" + LINE)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('"action": "noop"', result.stdout)
        self.assertIn("No change", result.stdout)

    def test_a_secret_without_a_line_does_not_rotate(self) -> None:
        result = self.plan(True, "")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn('"action": "fail"', result.stdout)
        self.assertIn("Refusing to rotate", result.stdout)

    def test_a_line_without_a_secret_does_not_create_a_new_key(self) -> None:
        result = self.plan(False, LINE)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Refusing to create a new key", result.stdout)

    def test_a_malformed_governance_ci_line_is_not_treated_as_absent(self) -> None:
        result = self.plan(False, "governance-ci ssh-ed25519 " + ("A" * 48) + "\n")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("error", result.stdout)
        self.assertNotIn('"action": "create"', result.stdout)

    def test_two_governance_ci_lines_are_refused(self) -> None:
        result = self.plan(True, LINE + LINE)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("more than one", result.stdout)


class SignerSetupWorkflow(unittest.TestCase):
    def test_the_workflow_stays_on_main_and_does_not_print_the_private_key(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("branches: [main]", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn(".github/workflows/signer-setup.yml", text)
        self.assertIn("scripts/stagectl", text)
        self.assertNotIn("pull_request", text)
        self.assertNotIn("contents: write", text)
        self.assertIn("contents: read", text)
        self.assertIn("GOVERNANCE_SETUP_TOKEN", text)
        self.assertIn("gh secret set GOVERNANCE_VERDICT_KEY", text)
        self.assertIn("signer-setup-plan", text)
        self.assertIn("signer-line", text)
        self.assertIn("::add-mask::", text)
        secret_set = "\n".join(line for line in text.splitlines() if "secret set" in line)
        self.assertNotIn("--body", secret_set)
        self.assertNotIn("--force", text)
        self.assertIn("governance-ci-signer", text)
        self.assertNotIn("pull_request_target", text)


if __name__ == "__main__":
    unittest.main()
