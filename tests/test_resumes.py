import unittest
from assistant.resumes import validate_edits, replacement_requests, clone_requests


class ResumeTest(unittest.TestCase):
    def test_utf16_positions_and_reverse_order(self):
        text = 'Name 😀 Python and SQL\n'
        edits = [{'before': 'Python', 'after': 'Python ETL'}, {'before': 'SQL', 'after': 'SQL workflows'}]
        expected, requests = replacement_requests(text, edits, 'owned-tab')
        self.assertEqual(expected, 'Name 😀 Python ETL and SQL workflows\n')
        self.assertEqual(requests[-1]['insertText']['location']['index'], 9)
        self.assertTrue(all('owned-tab' in str(request) for request in requests))

    def test_citations_and_unique_edits(self):
        edit = {'before': 'Python', 'after': 'Python ETL', 'source_id': 'r', 'quote': 'Python ETL'}
        sources = [{'id': 'r', 'text': 'Built Python ETL'}]
        self.assertEqual(len(validate_edits({'edits': [edit]}, 'Python\n', sources)), 1)
        for text, changed in [('Python Python', edit), ('Python', {**edit, 'quote': 'invented'})]:
            with self.assertRaises(ValueError):
                validate_edits({'edits': [changed]}, text, sources)

    def test_clone_rejects_tables_before_writing(self):
        tab = {'documentTab': {'body': {'content': [{'table': {}}]}}}
        with self.assertRaises(ValueError):
            clone_requests(tab, 'target')

    def test_clone_preserves_simple_text_style(self):
        tab = {'documentTab': {'body': {'content': [{'paragraph': {'paragraphStyle': {'namedStyleType': 'NORMAL_TEXT'},
            'elements': [{'textRun': {'content': 'Python\n', 'textStyle': {'bold': True}}}]}}]}}}
        text, requests = clone_requests(tab, 'target')
        self.assertEqual(text, 'Python\n')
        self.assertEqual(requests[0]['insertText']['text'], 'Python')
        self.assertEqual(requests[1]['updateTextStyle']['textStyle'], {'bold': True})
