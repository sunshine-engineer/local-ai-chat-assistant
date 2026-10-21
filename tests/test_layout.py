import copy
import json
import tempfile
import unittest
from unittest.mock import Mock

from assistant.jobs import Jobs
from assistant.layout import format_resume, verify_compact
from assistant.state import Store


def formatted_tab():
    return {'documentStyle': {k: {'magnitude': 36, 'unit': 'PT'} for k in
        ('marginTop', 'marginBottom', 'marginLeft', 'marginRight')},
        'body': {'content': [{'paragraph': {'paragraphStyle': {'lineSpacing': 105,
            'spaceAbove': {'magnitude': 0, 'unit': 'PT'}, 'spaceBelow': {'magnitude': 2, 'unit': 'PT'}},
            'elements': [{'textRun': {'content': 'Resume text\n',
                'textStyle': {'fontSize': {'magnitude': 10.5, 'unit': 'PT'}, 'bold': True}}}]}}]}}


class LayoutTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.google = Mock()
        self.jobs = Jobs(Store(directory.name), self.google)
        self.app = {'reviewed': True, 'approved_text_hash': 'old', 'draft': {
            'ready': True, 'title': 'Assistant — app', 'doc_id': 'copy', 'tab_id': 'owned', 'url': 'draft-url'}}
        self.jobs.save('app', self.app)
        self.doc = {'revisionId': 'r1', 'tabs': [
            {'tabProperties': {'tabId': 'owned', 'title': 'Assistant — app'}, 'documentTab': formatted_tab()},
            {'tabProperties': {'tabId': 'source'}, 'documentTab': {'body': {'content': []}}}]}
        self.google.document.return_value = self.doc

    def test_preview_keeps_approval_and_has_no_google_calls(self):
        result = json.loads(format_resume(self.jobs, 'app'))
        self.assertEqual(result['write_command'], '/format_resume app --write')
        self.assertTrue(self.jobs.application('app')[1]['reviewed'])
        self.google.document.assert_not_called()
        self.google.batch.assert_not_called()

    def test_write_targets_only_owned_tab_and_requires_new_approval(self):
        format_resume(self.jobs, 'app --write')
        args = self.google.batch.call_args.args
        self.assertEqual((args[0], args[2]), ('copy', 'r1'))
        for request in args[1]:
            update = next(iter(request.values()))
            self.assertEqual(update.get('tabId') or update['range']['tabId'], 'owned')
        self.assertFalse(self.jobs.application('app')[1]['reviewed'])
        self.assertNotIn('approved_text_hash', self.jobs.application('app')[1])

    def test_timeout_invalidates_approval_and_same_command_can_retry(self):
        self.google.batch.side_effect = ValueError('Remote result uncertain')
        with self.assertRaises(ValueError):
            format_resume(self.jobs, 'app --write')
        self.assertFalse(self.jobs.application('app')[1]['reviewed'])
        self.google.batch.side_effect = None
        format_resume(self.jobs, 'app --write')

    def test_refuses_pending_edits_and_unowned_tab(self):
        self.app['pending_edits'] = {'before': 'old'}
        self.jobs.save('app', self.app)
        with self.assertRaisesRegex(ValueError, 'pending edits'):
            format_resume(self.jobs, 'app --write')
        self.app.pop('pending_edits')
        self.jobs.save('app', self.app)
        self.doc['tabs'][0]['tabProperties']['title'] = 'General Resume'
        with self.assertRaisesRegex(ValueError, 'owned draft'):
            format_resume(self.jobs, 'app --write')
        self.google.batch.assert_not_called()

    def test_detects_changed_text_or_unrelated_tab(self):
        for target in ('text', 'other-tab'):
            after = copy.deepcopy(self.doc)
            if target == 'text':
                after['tabs'][0]['documentTab']['body']['content'][0]['paragraph']['elements'][0]['textRun']['content'] = 'Changed\n'
            else:
                after['tabs'][1]['documentTab']['changed'] = True
            self.google.document.side_effect = [self.doc, after]
            with self.assertRaisesRegex(ValueError, 'verification failed'):
                format_resume(self.jobs, 'app --write')

    def test_rejects_incomplete_style_readback(self):
        tab = formatted_tab()
        tab['documentStyle']['marginTop']['magnitude'] = 50
        with self.assertRaisesRegex(ValueError, 'margin readback'):
            verify_compact(tab)

    def test_accepts_google_float_rounding_and_omitted_zero(self):
        tab = formatted_tab()
        style = tab['body']['content'][0]['paragraph']['paragraphStyle']
        style['lineSpacing'] = 104.99999
        style['spaceAbove'] = {'unit': 'PT'}
        verify_compact(tab)
