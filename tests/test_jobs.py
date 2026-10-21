import tempfile
import unittest
from assistant.state import Store
from assistant.jobs import Jobs


class FakeGoogle:
    def __init__(self):
        self.calls = []
    def create_document(self, folder, title, key, text):
        self.calls.append((folder, key, text))
        return 'https://docs.google.com/document/d/fake/edit'


class JobsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.google = FakeGoogle()
        self.jobs = Jobs(self.store, self.google)

    def test_capture_retry_and_preservation(self):
        self.jobs.configure('{"jd_folder_id":"folder"}')
        payload = '{"jd":"Original JD with exact wording"}'
        first = self.jobs.save_jd(payload)
        self.assertEqual(first, self.jobs.save_jd(payload))
        self.assertIn('Original JD with exact wording', self.google.calls[0][2])
        self.assertIn('Company unknown', self.google.calls[0][2])
        self.assertEqual(self.google.calls[0][1], self.google.calls[1][1])

    def test_configuration_validation(self):
        for payload in ['[]', '{"jd_folder_id":"https://example.com"}', '{"unknown":1}', '{"source_folder_ids":"x"}']:
            with self.assertRaises(ValueError):
                self.jobs.configure(payload)
        with self.assertRaises(ValueError):
            self.jobs.save_jd('{"jd":""}')
        with self.assertRaises(ValueError):
            self.jobs.application('missing')

    def test_state_survives_failed_action(self):
        with self.assertRaises(ValueError):
            with self.store.action_lock():
                self.store.put('checkpoint', 'saved')
                raise ValueError('network')
        self.assertEqual(Store(self.temp.name).get('checkpoint'), 'saved')
