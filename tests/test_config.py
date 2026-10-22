"""Validate default compatibility and dynamic environment configuration overrides.

File: tests/test_config.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import json
import os
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from assistant.config import defaults, setting
from assistant.google import Google
from assistant.model import generate_json


class ConfigTest(unittest.TestCase):
    """Exercise configuration resolution without a network or real credentials."""

    def test_defaults_preserve_previous_runtime_values(self):
        """Verify packaged defaults match the prior local runtime behavior."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(setting("ollama", "host", "OLLAMA_HOST"), "http://localhost:11434")
            self.assertEqual(setting("ollama", "model", "OLLAMA_MODEL"), "qwen3:1.7b")
            self.assertEqual(setting("google", "timeout_seconds", "GOOGLE_TIMEOUT_SECONDS"), 60)
            self.assertEqual(setting("workflow", "home", "ASSISTANT_HOME"), ".assistant")
            self.assertEqual(defaults()["tracker"]["timezone"], "Asia/Kolkata")

    def test_overrides_are_typed_and_not_frozen_at_import(self):
        """Verify changed environment settings are observed without re-importing modules."""
        with patch.dict(os.environ, {"OLLAMA_CONTEXT": "2048"}):
            self.assertEqual(setting("ollama", "context", "OLLAMA_CONTEXT"), 2048)
        with patch.dict(os.environ, {"OLLAMA_CONTEXT": "4096"}):
            self.assertEqual(setting("ollama", "context", "OLLAMA_CONTEXT"), 4096)
        with patch.dict(os.environ, {"OLLAMA_CONTEXT": "invalid"}):
            with self.assertRaises(ValueError):
                setting("ollama", "context", "OLLAMA_CONTEXT")

    def test_model_request_uses_configured_endpoint_and_budgets(self):
        """Verify non-default provider settings reach the structured request unchanged."""
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps({"done": True, "response": '{"ok":true}'}).encode()
        environment = {
            "OLLAMA_HOST": "http://model.test:1234",
            "OLLAMA_MODEL": "test-model",
            "OLLAMA_CONTEXT": "2048",
            "OLLAMA_OUTPUT_TOKENS": "256",
            "OLLAMA_TIMEOUT_SECONDS": "12.5",
        }
        with (
            patch.dict(os.environ, environment),
            patch("assistant.model.urlopen", return_value=response) as request,
        ):
            self.assertEqual(generate_json("Test", {}), {"ok": True})
        call = request.call_args
        self.assertEqual(call.kwargs["timeout"], 12.5)
        self.assertEqual(call.args[0].full_url, "http://model.test:1234/api/generate")
        self.assertEqual(json.loads(call.args[0].data)["options"]["num_ctx"], 2048)

    def test_google_timeout_override_uses_injected_session(self):
        """Verify the configurable Google timeout without making a provider request."""
        session = Mock()
        session.request.return_value = Mock(ok=True, content=b"{}")
        session.request.return_value.json.return_value = {}
        with patch.dict(os.environ, {"GOOGLE_TIMEOUT_SECONDS": "9.5"}):
            Google(".", session).call("GET", "https://example.test/read-only")
        self.assertEqual(session.request.call_args.kwargs["timeout"], 9.5)

    def test_database_fallback_encodes_custom_credentials(self):
        """Verify custom PostgreSQL fields survive URL construction in a fresh process."""
        script = """
from postgres.db import engine
assert engine.url.username == 'synthetic-user'
assert engine.url.password == 'synthetic:@/password'
assert engine.url.database == 'synthetic-db'
assert engine.url.host == 'db.test'
engine.dispose()
"""
        environment = {
            **os.environ,
            "DATABASE_URL": "",
            "DB_HOST": "db.test",
            "DB_USER": "synthetic-user",
            "DB_PASSWORD": "synthetic:@/password",
            "DB_NAME": "synthetic-db",
        }
        result = subprocess.run(
            [sys.executable, "-c", script], env=environment, capture_output=True, timeout=20
        )
        self.assertEqual(result.returncode, 0, "Custom database configuration failed")

    def test_database_initialization_entrypoint_is_repeatable(self):
        """Verify the reorganized initializer preserves records across repeated execution."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            environment = {
                **os.environ,
                "DATABASE_URL": "sqlite:///" + str(Path(directory) / "chat.db"),
            }
            for _ in range(2):
                result = subprocess.run(
                    [sys.executable, "-m", "postgres.initialize"],
                    env=environment,
                    capture_output=True,
                    timeout=20,
                )
                self.assertEqual(result.returncode, 0, "Database initialization failed")
            script = "from helpers import create_chat_session, get_sessions; create_chat_session(); assert len(get_sessions()) == 1"
            result = subprocess.run(
                [sys.executable, "-c", script], env=environment, capture_output=True, timeout=20
            )
            self.assertEqual(
                result.returncode, 0, "Initialized database could not persist a session"
            )
            subprocess.run(
                [sys.executable, "-m", "postgres.initialize"],
                env=environment,
                check=True,
                capture_output=True,
                timeout=20,
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from helpers import get_sessions; assert len(get_sessions()) == 1",
                ],
                env=environment,
                capture_output=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, "Repeated initialization lost a session")

    def test_importing_ui_does_not_initialize_chat_database(self):
        """Verify UI definitions can be imported without executing the application entry point."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "not-created.db"
            environment = {**os.environ, "DATABASE_URL": "sqlite:///" + str(database)}
            result = subprocess.run(
                [sys.executable, "-c", "import app"],
                env=environment,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, "UI module import failed")
            self.assertFalse(database.exists())
