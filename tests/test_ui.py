"""Offline Streamlit smoke test; no credentials or model service needed."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class UiTest(unittest.TestCase):
    def test_commands_render_and_history_survives_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'ASSISTANT_HOME': directory,
                                         'DATABASE_URL': 'sqlite:///' + str(Path(directory) / 'chat.db')}):
                app = AppTest.from_file(str(ROOT / 'app.py')).run()
                self.assertFalse(app.exception)
                app.chat_input[0].set_value('/help').run()
                self.assertFalse(app.exception)
                self.assertTrue(any('/reset_edits' in item.value for item in app.markdown))
                app.chat_input[0].set_value('/unknown_action').run()
                self.assertFalse(app.exception)
                self.assertTrue(any('Unknown command' in item.value for item in app.markdown))
                self.assertTrue(any('/reset_edits' in item.value for item in app.markdown))

                from postgres.db import engine
                engine.dispose()
