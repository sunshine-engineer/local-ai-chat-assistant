"""Exercise actual Streamlit inspection without Google, a model or decision writes."""
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest
from assistant.jobs import Jobs
from assistant.state import Store
from assistant.evidence import compare, digest
from assistant.comparison_review import review
from assistant.requirements import review as review_requirements


class ReviewUiTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {'ASSISTANT_HOME': directory.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.cloud = Mock()
        google = patch('assistant.jobs.Google', return_value=self.cloud)
        google.start()
        self.addCleanup(google.stop)
        model = patch('assistant.model.generate_json', side_effect=AssertionError('Viewer invoked model'))
        model.start()
        self.addCleanup(model.stop)
        self.jobs = Jobs(Store(), self.cloud)
        self.source = {'id': 'resume', 'kind': 'resume', 'title': 'Synthetic resume',
            'text': 'Avery Example\nBuilt Python ETL.\nNext steps: add Kubernetes.', 'url': 'synthetic://resume'}
        self.project = {'id': 'project', 'kind': 'evidence', 'title': 'Synthetic project',
            'text': 'Independent Python prototype.', 'url': 'synthetic://project'}
        self.jobs.save('app', {'input': {'jd': 'Required: Python ETL.'}})
        review_requirements(self.jobs, '{"application_id":"app","candidate_ids":[0],"reviewed":true}')
        self.jobs.store.put('catalogue', {'sources': [self.source, self.project],
                                       'digest': digest([self.source, self.project])})
        compare(self.jobs, 'app', lambda instruction, data, **kwargs: {'matches': [
            {'requirement': data['requirements'][0], 'status': 'supported',
             'quote': data['source'].splitlines()[0]}]})
        self.app = AppTest.from_string('from assistant.review_ui import render_comparison_review\nrender_comparison_review()').run()

    def load(self, app_id='app'):
        self.app.text_input[0].set_value(app_id)
        self.app.button[0].click().run()
        self.assertFalse(self.app.exception)

    def test_inspection_keeps_bad_proposals_distinct_and_never_writes_decisions(self):
        before = self.jobs.application('app')[1]
        self.load()
        text = '\n'.join(item.value for item in self.app.text)
        self.assertIn('None — review required', text)
        self.assertIn('Accepted reviewer counts: Not established', text)
        self.assertIn('no_specific_term_overlap', text)
        self.assertIn('No decision recorded', text)
        code = [item.value for item in self.app.code]
        self.assertIn(self.source['text'], code)
        template = json.loads(code[-1])
        self.assertEqual(template['source_id'], 'resume')
        self.assertEqual(template['decisions'][0]['status'], 'CHOOSE supported|partial|gap')
        self.app.selectbox[0].select('project').run()
        template = json.loads(self.app.code[-1].value)
        self.assertEqual(template['source_id'], 'project')
        self.assertEqual(self.jobs.application('app')[1], before)
        self.cloud.document.assert_not_called()
        self.cloud.batch.assert_not_called()
        self.cloud.create_document.assert_not_called()

    def test_reload_shows_recorded_correction_and_original_proposal(self):
        self.load()
        comparison = self.jobs.application('app')[1]['comparison']
        review(self.jobs, json.dumps({'application_id': 'app', 'comparison_id': comparison['comparison_id'],
            'source_id': 'resume', 'reviewed': True, 'decisions': [{'requirement_id': 0,
            'status': 'supported', 'quote': 'Built Python ETL.', 'note': 'Explicit completed work.'}]}))
        self.load()
        self.assertIn('Avery Example', [item.value for item in self.app.code])
        self.assertIn('Built Python ETL.', [item.value for item in self.app.code])
        self.assertTrue(any('Explicit completed work.' in item.value for item in self.app.text))
        self.assertTrue(any('"supported": 1' in item.value for item in self.app.text))

    def test_application_change_and_failed_reload_do_not_show_old_evidence(self):
        self.load()
        self.app.text_input[0].set_value('missing').run()
        self.assertEqual(len(self.app.code), 0)
        self.load('missing')
        self.assertEqual(len(self.app.code), 0)
        self.assertTrue(self.app.error)
        self.load('app extra')
        self.assertTrue(any('one application ID' in item.value for item in self.app.error))

    def test_requirement_navigation_does_not_reuse_another_requirements_quote(self):
        self.jobs.save('two', {'input': {'jd': 'Required: Python ETL. Required: Docker.'}})
        review_requirements(self.jobs, '{"application_id":"two","candidate_ids":[0,1],"reviewed":true}')
        compare(self.jobs, 'two', lambda instruction, data, **kwargs: {'matches': [
            {'requirement': requirement, 'status': 'supported' if 'Python' in requirement else 'gap',
             'quote': data['source'].splitlines()[0] if 'Python' in requirement else ''}
            for requirement in data['requirements']]})
        self.load('two')
        self.assertIn('Avery Example', [item.value for item in self.app.code])
        self.app.selectbox[1].select(1).run()
        self.assertFalse(self.app.exception)
        self.assertIn('(No supporting quotation)', [item.value for item in self.app.code])
        self.assertNotIn('Avery Example', [item.value for item in self.app.code])
        self.assertTrue(any(item.value == 'Required: Docker.' for item in self.app.text))
