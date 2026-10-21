import unittest
from unittest.mock import Mock
from assistant.google import Google, FOLDER, tabs, body_text


def document(text='\n'):
    return {'revisionId': 'revision1', 'tabs': [{'tabProperties': {'tabId': 't1'},
        'documentTab': {'body': {'content': [{'paragraph': {'elements': [{'textRun': {'content': text}}]}}]}}}]}


class MemoryGoogle(Google):
    def __init__(self):
        super().__init__('.')
        self.sandbox_folder_id = 'folder'
        self.text, self.created, self.writes = '\n', False, 0
    def metadata(self, file_id):
        return {'mimeType': FOLDER}
    def files(self, query):
        return [{'id': 'doc'}] if self.created else []
    def call(self, method, url, **kwargs):
        self.created = True
        return {'id': 'doc'}
    def document(self, doc_id):
        return document(self.text)
    def batch(self, doc_id, requests, revision):
        self.writes += 1
        self.text = requests[0]['insertText']['text'] + '\n'


class GoogleTest(unittest.TestCase):
    def test_disabled_api_diagnostic_excludes_raw_response(self):
        response = Mock(ok=False, status_code=403)
        response.json.return_value = {'error': {'message': 'PRIVATE RESPONSE', 'details': [
            {'reason': 'SERVICE_DISABLED', 'metadata': {'service': 'docs.googleapis.com', 'consumer': 'PRIVATE PROJECT'}}]}}
        session = Mock()
        session.request.return_value = response
        with self.assertRaisesRegex(ValueError, 'API disabled: docs.googleapis.com') as error:
            Google('.', session).call('GET', 'https://docs.googleapis.com/v1/documents/test')
        self.assertNotIn('PRIVATE', str(error.exception))

    def test_retry_reconciles_completed_remote_write(self):
        google = MemoryGoogle()
        url = google.create_document('folder', 'Title', 'key', 'Original\n')
        self.assertEqual(url, google.create_document('folder', 'Title', 'key', 'Original\n'))
        self.assertEqual(google.writes, 1)
        google.text = 'Human edit\n'
        with self.assertRaisesRegex(ValueError, 'edited externally'):
            google.create_document('folder', 'Title', 'key', 'Original\n')
        self.assertEqual(google.writes, 1)
