import unittest
from assistant.commands import Action, CommandRegistry


class CommandsTest(unittest.TestCase):
    def test_routing_and_multiline_payload(self):
        registry = CommandRegistry()
        registry.register(Action('echo', 'Echo', lambda s: s))
        self.assertEqual(registry.execute('/echo line one\nline two'), 'line one\nline two')
        self.assertIsNone(registry.execute('ordinary chat'))
        self.assertIn('Unknown command', registry.execute('/missing'))
        self.assertIn('/echo', registry.execute('/help'))

    def test_duplicate_and_failure(self):
        registry = CommandRegistry()
        with self.assertRaises(ValueError):
            registry.register(Action('help', '', str))
        def fail(s):
            raise ValueError('Missing input')
        registry.register(Action('fail', '', fail))
        self.assertEqual(registry.execute('/fail'), 'Action failed: Missing input')
