import json
import tempfile
import unittest
from unittest.mock import Mock

from assistant.jobs import Jobs
from assistant.state import Store
from assistant.requirements import candidates, review, selected, show
from assistant.evidence import compare, assess


class RequirementsTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.jobs = Jobs(Store(directory.name), Mock())
        self.jd = 'We serve millions of learners.\nRequired: Python and FastAPI.\nRAG is desirable.\nProduction Kubernetes required.'
        self.jobs.save('app', {'input': {'jd': self.jd}})

    def payload(self, ids, **kwargs):
        return json.dumps({'application_id': 'app', 'candidate_ids': ids, 'reviewed': True, **kwargs})

    def test_candidates_include_marketing_and_every_technical_sentence(self):
        result = json.loads(show(self.jobs, 'app'))
        self.assertEqual([r['text'] for r in result['candidates']], self.jd.splitlines())
        self.assertFalse(result['reviewed'])
        self.jobs.google.document.assert_not_called()

    def test_selection_is_literal_and_keeps_desirable_and_missing_skills(self):
        review(self.jobs, self.payload([3, 1, 2]))
        app = self.jobs.application('app')[1]
        self.assertEqual(selected(app), self.jd.splitlines()[1:])
        self.assertTrue(json.loads(show(self.jobs, 'app'))['reviewed'])

    def test_comparison_refuses_unreviewed_jd_before_model_call(self):
        self.jobs.store.put('catalogue', {'sources': [], 'digest': 'test'})
        model = Mock()
        with self.assertRaisesRegex(ValueError, 'Review JD scope'):
            compare(self.jobs, 'app', model)
        model.assert_not_called()

    def test_invalid_or_unconfirmed_selection_is_rejected(self):
        for ids in ([], [True], [-1], [99], [1, 1], 'all'):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                review(self.jobs, self.payload(ids))
        with self.assertRaises(ValueError):
            review(self.jobs, self.payload([1], reviewed=False))

    def test_changed_jd_invalidates_review(self):
        review(self.jobs, self.payload([1, 2, 3]))
        app = self.jobs.application('app')[1]
        app['input']['jd'] += '\nRedis required.'
        with self.assertRaisesRegex(ValueError, 'Review JD scope'):
            selected(app)

    def test_reselection_clears_stale_comparison_and_freezes_after_artifact(self):
        app = self.jobs.application('app')[1]
        app.update({'comparison': {'old': True}, 'source_snapshot': ['old']})
        self.jobs.save('app', app)
        review(self.jobs, self.payload([1, 2]))
        app = self.jobs.application('app')[1]
        self.assertNotIn('comparison', app)
        self.assertNotIn('source_snapshot', app)
        for key in ('draft', 'cover_letter_draft'):
            app[key] = {'exists': True}
            self.jobs.save('app', app)
            with self.assertRaisesRegex(ValueError, 'fixed once'):
                review(self.jobs, self.payload([1]))
            app.pop(key)

    def test_oversized_candidate_list_fails_without_silent_truncation(self):
        with self.assertRaisesRegex(ValueError, 'shorter JD'):
            candidates({'input': {'jd': '\n'.join('Requirement '+str(i) for i in range(201))}})

    def test_batched_comparison_preserves_complete_selected_scope(self):
        calls = []
        def model(instruction, data, **kwargs):
            calls.append(data['requirements'])
            return {'matches': [{'requirement': r, 'status': 'gap', 'quote': ''} for r in data['requirements']]}
        from unittest.mock import patch
        rows = ['Required '+str(i) for i in range(7)]
        with patch.dict('os.environ', {'ASSISTANT_REQUIREMENT_BATCH_SIZE': '3'}):
            result = assess(rows, 'Source text.', 'resume', model)
        self.assertEqual([r['requirement'] for r in result], rows)
        self.assertEqual([len(batch) for batch in calls], [3, 3, 1])

    def test_missing_batch_match_cannot_be_saved_as_comparison(self):
        model = Mock(return_value={'matches': []})
        with self.assertRaisesRegex(ValueError, 'every extracted requirement'):
            assess(['Required Python'], 'Source text.', 'resume', model)
