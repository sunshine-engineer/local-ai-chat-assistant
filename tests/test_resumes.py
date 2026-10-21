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

    def test_clone_styles_target_only_new_tab_and_skip_read_only_flags(self):
        tab = {'documentTab': {'documentStyle': {'pageSize': {'width': {'magnitude': 612, 'unit': 'PT'}},
            'useCustomHeaderFooterMargins': True}, 'namedStyles': {'styles': [{'namedStyleType': 'NORMAL_TEXT',
            'textStyle': {'fontSize': {'magnitude': 11, 'unit': 'PT'}}}]},
            'body': {'content': [{'paragraph': {'elements': [{'textRun': {'content': 'Text\n'}}]}}]}}}
        _, requests = clone_requests(tab, 'new-tab')
        doc_style = next(r['updateDocumentStyle'] for r in requests if 'updateDocumentStyle' in r)
        self.assertIn('pageSize', doc_style['documentStyle'])
        self.assertNotIn('useCustomHeaderFooterMargins', doc_style['documentStyle'])
        self.assertEqual(doc_style['tabId'], 'new-tab')
        named_style = next(r['updateNamedStyle'] for r in requests if 'updateNamedStyle' in r)
        self.assertEqual(named_style['tabId'], 'new-tab')

    def test_tailoring_protects_detected_name_and_contact_lines(self):
        text='Avery Example\nuser@example.com\nBuilt Python ETL.\n'
        source=[{'id':'r','text':'Built Python ETL.'}]
        for before in ('Avery Example','user@example.com','Avery'):
            edit={'before':before,'after':'Python engineer','source_id':'r','quote':'Built Python ETL.'}
            with self.assertRaisesRegex(ValueError,'name/contact'):
                validate_edits({'edits':[edit]},text,source)
        from assistant.schemas import edits_for
        choices=edits_for(text,source)['properties']['edits']['items']['properties']['before']['enum']
        self.assertEqual(choices,['Built Python ETL.'])
        from jsonschema import Draft202012Validator
        schema=edits_for('Avery Example\nuser@example.com\n',source)
        Draft202012Validator.check_schema(schema)
        self.assertEqual(schema['properties']['edits']['maxItems'],0)

    def test_unsupported_new_numeric_claims_are_rejected(self):
        source=[{'id':'r','text':'Built Python ETL.'}]
        edit={'before':'Built Python ETL.','after':'Built 100 Python ETL pipelines.','source_id':'r','quote':'Built Python ETL.'}
        with self.assertRaisesRegex(ValueError,'numerical claims'):
            validate_edits({'edits':[edit]},'Built Python ETL.\n',source)
