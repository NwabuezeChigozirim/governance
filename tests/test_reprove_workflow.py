"""The automatic re-proof workflow stays on the trusted side of the secret."""

import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "reprove.yml"


class ReproveWorkflow(unittest.TestCase):
    def test_the_workflow_keeps_the_signing_key_away_from_the_checks(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("pull_request_target:", text)
        self.assertIn("workflow_run:", text)
        self.assertIn('workflows: ["Verify"]', text)
        self.assertIn("head_repository.full_name == github.repository", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("--defer-signature", text)
        self.assertIn("sign-verdict", text)
        self.assertIn("GOVERNANCE_VERDICT_KEY", text)
        self.assertEqual(text.count("contents: write"), 1)
        reprove = text.split("  reprove:", 1)[1].split("  publish:", 1)[0]
        publish = text.split("  publish:", 1)[1]
        self.assertNotIn("GOVERNANCE_VERDICT_KEY", reprove)
        self.assertNotIn("sign-verdict", reprove)
        self.assertNotIn("reprove ", publish)
        self.assertNotIn("run-check", publish)
        self.assertIn("secrets.GOVERNANCE_VERDICT_KEY == ''", publish)
        self.assertIn("exit 1", publish)


if __name__ == "__main__":
    unittest.main()
