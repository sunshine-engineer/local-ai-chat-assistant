"""Regression coverage for commands.

File: tests/test_commands.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import unittest

from assistant.commands import Action, CommandRegistry


class CommandsTest(unittest.TestCase):
    """Exercise commands contracts using isolated fixtures."""

    def test_routing_and_multiline_payload(self):
        """Verify routing and multiline payload."""
        registry = CommandRegistry()
        registry.register(Action("echo", "Echo", lambda s: s))
        self.assertEqual(registry.execute("/echo line one\nline two"), "line one\nline two")
        self.assertIsNone(registry.execute("ordinary chat"))
        self.assertIn("Unknown command", registry.execute("/missing"))
        self.assertIn("/echo", registry.execute("/help"))

    def test_duplicate_and_failure(self):
        """Verify duplicate and failure."""
        registry = CommandRegistry()
        with self.assertRaises(ValueError):
            registry.register(Action("help", "", str))

        def fail(s):
            """Simulate an expected command-validation failure.

            Args:
                s: Command argument string supplied to the failing test handler.

            Raises:
                ValueError: The explicit fixture invariant or expected-failure path is violated.
            """
            raise ValueError("Missing input")

        registry.register(Action("fail", "", fail))
        self.assertEqual(registry.execute("/fail"), "Action failed: Missing input")
