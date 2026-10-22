"""Offline Streamlit smoke test; no credentials or model service needed.

File: tests/test_ui.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class UiTest(unittest.TestCase):
    """Exercise ui contracts using isolated fixtures."""

    def test_commands_render_and_history_survives_rerun(self):
        """Verify commands render and history survives rerun."""
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {
                    "ASSISTANT_HOME": directory,
                    "CHAT_TEMPERATURE": "0.2",
                    "CHAT_MAX_TOKENS": "100",
                    "DATABASE_URL": "sqlite:///" + str(Path(directory) / "chat.db"),
                },
            ):
                app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=15)
                self.assertFalse(app.exception)
                self.assertEqual([slider.value for slider in app.slider], [0.2, 100])
                app.chat_input[0].set_value("/help").run(timeout=15)
                self.assertFalse(app.exception)
                self.assertTrue(any("/reset_edits" in item.value for item in app.markdown))
                app.chat_input[0].set_value("/unknown_action").run(timeout=15)
                self.assertFalse(app.exception)
                self.assertTrue(any("Unknown command" in item.value for item in app.markdown))
                self.assertTrue(any("/reset_edits" in item.value for item in app.markdown))

                from langchain_core.runnables import RunnableLambda

                with patch(
                    "langchain_ollama.OllamaLLM",
                    return_value=RunnableLambda(lambda _: "Offline chat reply"),
                ):
                    app.chat_input[0].set_value("Test ordinary chat").run(timeout=15)
                    self.assertFalse(app.exception)
                    self.assertTrue(
                        any(item.value == "Offline chat reply" for item in app.markdown)
                    )
                import streamlit as st

                st.cache_resource.clear()

                from postgres.db import engine

                engine.dispose()
