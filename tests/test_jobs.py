"""Regression coverage for jobs.

File: tests/test_jobs.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import tempfile
import unittest

from assistant.jobs import Jobs
from assistant.state import Store


class FakeGoogle:
    """Provide an explicit in-memory provider double for deterministic tests."""

    def __init__(self):
        """Initialize the in-memory provider state and request counters."""
        self.calls = []

    def create_document(self, folder, title, key, text):
        """Create a synthetic document and retain its content for readback.

        Args:
            folder: Destination sandbox folder identifier.
            title: Human-readable document, tab or chat title.
            key: Stable record, schema-field or remote reconciliation key.
            text: Text to inspect or transform without changing the original value.

        Returns:
            Verified Google Docs URL.
        """
        self.calls.append((folder, key, text))
        return "https://docs.google.com/document/d/fake/edit"


class JobsTest(unittest.TestCase):
    """Exercise jobs contracts using isolated fixtures."""

    def setUp(self):
        """Create isolated temporary state and explicit provider fixtures for each test."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.google = FakeGoogle()
        self.jobs = Jobs(self.store, self.google)

    def test_capture_retry_and_preservation(self):
        """Verify capture retry and preservation."""
        self.jobs.configure('{"jd_folder_id":"folder"}')
        payload = '{"jd":"Original JD with exact wording"}'
        first = self.jobs.save_jd(payload)
        self.assertEqual(first, self.jobs.save_jd(payload))
        self.assertIn("Original JD with exact wording", self.google.calls[0][2])
        self.assertIn("Company unknown", self.google.calls[0][2])
        self.assertEqual(self.google.calls[0][1], self.google.calls[1][1])

    def test_configuration_validation(self):
        """Verify configuration validation."""
        for payload in [
            "[]",
            '{"jd_folder_id":"https://example.com"}',
            '{"unknown":1}',
            '{"source_folder_ids":"x"}',
        ]:
            with self.assertRaises(ValueError):
                self.jobs.configure(payload)
        with self.assertRaises(ValueError):
            self.jobs.save_jd('{"jd":""}')
        with self.assertRaises(ValueError):
            self.jobs.application("missing")

    def test_variant_preserves_jd_and_original_application_and_retries_stably(self):
        """Verify variant preserves jd and original application and retries stably."""
        import json

        self.jobs.configure('{"jd_folder_id":"folder"}')
        original = {"jd": "Original exact JD", "url": "https://example.com/job"}
        first = self.jobs.save_jd(json.dumps(original))
        original_key = self.google.calls[-1][1]
        second = self.jobs.save_jd(json.dumps({**original, "variant": " controls-v1 "}))
        variant_key = self.google.calls[-1][1]
        self.assertNotEqual(original_key, variant_key)
        self.assertEqual(
            second, self.jobs.save_jd(json.dumps({**original, "variant": "controls-v1"}))
        )
        self.assertIn("Original job description\n\nOriginal exact JD\n", self.google.calls[-1][2])
        self.assertIn("Variant: controls-v1", self.google.calls[-1][2])
        self.assertEqual(first, self.jobs.save_jd(json.dumps(original)))
        for value in ("", "   ", "x" * 81):
            with self.assertRaises(ValueError):
                self.jobs.save_jd(json.dumps({**original, "variant": value}))

    def test_state_survives_failed_action(self):
        """Verify state survives failed action.

        Raises:
            ValueError: The explicit fixture invariant or expected-failure path is violated.
        """
        with self.assertRaises(ValueError):
            with self.store.action_lock():
                self.store.put("checkpoint", "saved")
                raise ValueError("network")
        self.assertEqual(Store(self.temp.name).get("checkpoint"), "saved")

    def test_transaction_rolls_back_and_connection_closes(self):
        """Verify transaction rolls back and connection closes.

        Raises:
            ValueError: The explicit fixture invariant or expected-failure path is violated.
        """
        import sqlite3

        with self.assertRaisesRegex(ValueError, "abort"):
            with self.store.connect() as db:
                db.execute("INSERT INTO records VALUES (?, ?)", ("uncommitted", "123"))
                raise ValueError("abort")
        self.assertIsNone(self.store.get("uncommitted"))
        with self.assertRaises(sqlite3.ProgrammingError):
            db.execute("SELECT 1")
        with self.store.action_lock():
            self.store.put("after_failure", "saved")
        with self.store.action_lock():
            self.assertEqual(self.store.get("after_failure"), "saved")
