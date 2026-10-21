"""CLI process tests verify public exit-code and stdin contracts without Google/model calls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = {**os.environ, 'ASSISTANT_HOME': self.temp.name}

    def run_cli(self, *args, stdin=''):
        return subprocess.run([sys.executable, '-m', 'assistant.cli', *args], input=stdin,
                              text=True, capture_output=True, cwd=ROOT, env=self.env, timeout=20)

    def test_help_unknown_and_missing_command_exit_codes(self):
        good = self.run_cli('/help')
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn('/reset_edits', good.stdout)
        bad = self.run_cli('/missing')
        self.assertEqual(bad.returncode, 1)
        self.assertIn('Unknown command', bad.stdout)
        self.assertEqual(self.run_cli().returncode, 2)

    def test_stdin_json_and_failed_action_exit(self):
        payload = {'sandbox_folder_id': 'sandbox', 'resume_tab_ids': ['t.example']}
        configured = self.run_cli('/configure', stdin=json.dumps(payload))
        self.assertEqual(configured.returncode, 0, configured.stderr)
        shown = self.run_cli('/sources')
        self.assertEqual(json.loads(shown.stdout), payload)
        failed = self.run_cli('/save_jd', stdin='{"jd":""}')
        self.assertEqual(failed.returncode, 1)
        self.assertIn('Action failed', failed.stdout)
