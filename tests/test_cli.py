"""CLI process tests verify public exit-code and stdin contracts without Google/model calls.

File: tests/test_cli.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CliTest(unittest.TestCase):
    """Exercise cli contracts using isolated fixtures."""

    def setUp(self):
        """Create isolated temporary state and explicit provider fixtures for each test."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = {**os.environ, "ASSISTANT_HOME": self.temp.name}

    def run_cli(self, *args, stdin=""):
        """Run the actual CLI in an isolated subprocess and capture its output.

        Args:
            stdin: Text piped to the CLI process.
            args: Additional CLI arguments or test callback positional arguments.

        Returns:
            Fixture value or structured response consumed by the regression.
        """
        return subprocess.run(
            [sys.executable, "-m", "assistant.cli", *args],
            input=stdin,
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=self.env,
            timeout=20,
        )

    def test_help_unknown_and_missing_command_exit_codes(self):
        """Verify help unknown and missing command exit codes."""
        good = self.run_cli("/help")
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("/reset_edits", good.stdout)
        bad = self.run_cli("/missing")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("Unknown command", bad.stdout)
        self.assertEqual(self.run_cli().returncode, 2)

    def test_stdin_json_and_failed_action_exit(self):
        """Verify stdin json and failed action exit."""
        payload = {"sandbox_folder_id": "sandbox", "resume_tab_ids": ["t.example"]}
        configured = self.run_cli("/configure", stdin=json.dumps(payload))
        self.assertEqual(configured.returncode, 0, configured.stderr)
        shown = self.run_cli("/sources")
        self.assertEqual(json.loads(shown.stdout), payload)
        failed = self.run_cli("/save_jd", stdin='{"jd":""}')
        self.assertEqual(failed.returncode, 1)
        self.assertIn("Action failed", failed.stdout)
