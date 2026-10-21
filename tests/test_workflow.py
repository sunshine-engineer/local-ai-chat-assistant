"""Integration of commands/state with explicit in-memory Google and model doubles."""
import copy
import json
import tempfile
import unittest
from urllib.parse import unquote
from assistant.jobs import Jobs
from assistant.state import Store
from assistant.google import DOC, FOLDER, body_text, tabs
from assistant import evidence, resumes, tracking, package, requirements, comparison_review


def make_tab(tab_id, text, title='General Resume'):
    return {'tabProperties': {'tabId': tab_id, 'title': title}, 'documentTab': {'body': {'content': [
        {'paragraph': {'paragraphStyle': {'namedStyleType': 'NORMAL_TEXT'}, 'elements': [
            {'textRun': {'content': text, 'textStyle': {'bold': False}}}]}}]}}}


class Cloud:
    def __init__(self):
        self.doc = {'revisionId': 'r1', 'tabs': [make_tab('source', 'Built Python ETL\n')]}
        self.rows = [tracking.HEADERS[:]]
        self.document_writes = self.row_writes = 0
        self.sandbox_folder_id = 'sandbox'
        self.fail_after_edit = False
        self.extra_docs = {}

    def check_write(self, file_id):
        if file_id not in ('resume-copy', 'tracker-copy'):
            raise ValueError('Outside sandbox')

    def document(self, file_id):
        if file_id in self.extra_docs:
            return copy.deepcopy(self.extra_docs[file_id])
        return copy.deepcopy(self.doc)

    def files(self, query):
        return []

    def create_document(self, folder, title, key, text):
        if folder != 'sandbox':
            raise ValueError('Outside sandbox')
        self.extra_docs[key] = {'tabs': [make_tab('t0', text)]}
        return 'https://docs.google.com/document/d/' + key + '/edit'

    def batch(self, doc_id, requests, revision):
        if revision != self.doc['revisionId']:
            raise ValueError('Revision conflict')
        self.document_writes += 1
        editing = False
        for request in requests:
            if 'addDocumentTab' in request:
                self.doc['tabs'].append(make_tab('draft', '\n', request['addDocumentTab']['tabProperties']['title']))
            elif 'insertText' in request or 'deleteContentRange' in request:
                editing = True
                data = request.get('insertText') or request['deleteContentRange']
                location = data.get('location') or data['range']
                target = resumes.find_tab(self.doc, location['tabId'])
                text = body_text(target['documentTab']['body'])
                encoded = text.encode('utf-16-le')
                start = (location.get('index', location.get('startIndex')) - 1) * 2
                if 'insertText' in request:
                    encoded = encoded[:start] + data['text'].encode('utf-16-le') + encoded[start:]
                else:
                    end = (location['endIndex'] - 1) * 2
                    encoded = encoded[:start] + encoded[end:]
                target['documentTab'] = make_tab('unused', encoded.decode('utf-16-le'))['documentTab']
        self.doc['revisionId'] += 'x'
        if editing and self.fail_after_edit:
            self.fail_after_edit = False
            raise ValueError('Connection lost after remote commit')

    def call(self, method, url, **kwargs):
        if '/values/' in url:
            a1 = unquote(url.split('/values/')[1]).split('!')[1]
            first, last = a1.split(':')
            start = int(''.join(filter(str.isdigit, first)))
            end = int(''.join(filter(str.isdigit, last)))
            if method == 'GET':
                return {'values': copy.deepcopy(self.rows[start - 1:end])}
            self.row_writes += 1
            while len(self.rows) < start:
                self.rows.append([])
            self.rows[start - 1] = kwargs['json']['values'][0][:]
            return {}
        if method == 'GET':
            return {'sheets': [{'properties': {'title': 'Assistant Applications', 'sheetId': 1}}]}
        raise AssertionError((method, url))


def comparison_model(instruction, data, **kwargs):
    return {'matches': [{'requirement': requirement, 'status': 'supported', 'quote': 'Built Python ETL'}
                        for requirement in data['requirements']]}


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cloud = Cloud()
        self.jobs = Jobs(Store(self.temp.name), self.cloud)
        self.jobs.configure(json.dumps({'sandbox_folder_id': 'sandbox', 'jd_folder_id': 'sandbox',
            'cover_letter_folder_id': 'sandbox', 'resume_doc_id': 'resume-copy',
            'tracker_id': 'tracker-copy', 'tracker_tab': 'Assistant Applications'}))
        self.jobs.save_jd('{"jd":"Python required","company":"Example","role":"Engineer","url":"https://example.com/job"}')
        import hashlib
        data = {'jd': 'Python required', 'company': 'Example', 'role': 'Engineer', 'url': 'https://example.com/job'}
        self.app_id = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
        evidence.refresh(self.jobs)
        requirements.review(self.jobs, json.dumps({'application_id': self.app_id,
            'candidate_ids': [0], 'reviewed': True}))
        evidence.compare(self.jobs, self.app_id, comparison_model)
        comparison = self.jobs.application(self.app_id)[1]['comparison']
        comparison_review.review(self.jobs, json.dumps({'application_id': self.app_id,
            'comparison_id': comparison['comparison_id'], 'source_id': 'resume-copy:source',
            'decisions': [{'requirement_id': 0, 'status': 'supported', 'quote': 'Built Python ETL',
                           'note': 'The source explicitly records Python ETL work.'}], 'reviewed': True}))

    def test_full_manual_flow_and_retries(self):
        resumes.draft(self.jobs, self.app_id)
        source_before = copy.deepcopy(self.cloud.doc['tabs'][0])
        resumes.suggest(self.jobs, self.app_id, lambda *args, **kwargs: {'edits': [{'before': 'Built Python ETL',
            'after': 'Built Python ETL workflows', 'source_id': 'resume-copy:source', 'quote': 'Built Python ETL'}]})
        command = json.dumps({'application_id': self.app_id, 'edit_ids': [0], 'edit_batch_id': self.jobs.application(self.app_id)[1]['suggestions']['edit_batch_id'], 'reviewed': True})
        # Simulate ambiguous remote success: state must reconcile rather than repeat edits.
        self.cloud.fail_after_edit = True
        with self.assertRaises(ValueError):
            resumes.apply(self.jobs, command)
        self.assertIsNotNone(self.jobs.application(self.app_id)[1]['pending_edits'])
        resumes.apply(self.jobs, command)
        write_count = self.cloud.document_writes
        resumes.apply(self.jobs, command)
        self.assertEqual(self.cloud.document_writes, write_count)
        self.assertEqual(source_before, self.cloud.doc['tabs'][0])
        with self.assertRaises(ValueError):
            tracking.track(self.jobs, self.app_id + ' --write')
        resumes.approve(self.jobs, self.app_id)
        preview = tracking.track(self.jobs, self.app_id)
        self.assertIn('Prepared', preview)
        self.assertEqual(self.cloud.row_writes, 0)
        tracking.track(self.jobs, self.app_id + ' --write')
        tracking.track(self.jobs, self.app_id + ' --write')
        self.assertEqual(self.cloud.row_writes, 1)
        self.assertEqual(len(self.cloud.rows), 2)
        self.assertEqual(self.cloud.rows[1][7], 'Prepared')
        result = json.loads(package.summary(self.jobs, self.app_id))
        self.assertEqual(result['status'], 'Prepared for you to apply')
        self.assertEqual(result['remaining'], [])

    def test_reject_changed_source_and_unapproved_or_stale_resume(self):
        self.cloud.doc['tabs'][0] = make_tab('source', 'External edit\n')
        with self.assertRaisesRegex(ValueError, 'changed since comparison'):
            resumes.draft(self.jobs, self.app_id)
        self.assertEqual(self.cloud.document_writes, 0)

    def test_cover_letter_citations_and_retry(self):
        def model(*args, **kwargs):
            return {'paragraphs': [{'text': 'I build Python ETL workflows.', 'source_id': 'resume-copy:source',
                                    'quote': 'Built Python ETL'}] * 2}
        package.cover_letter(self.jobs, self.app_id, model)
        def should_not_run(*args, **kwargs):
            raise AssertionError('Regenerated instead of retrying saved draft')
        result = package.cover_letter(self.jobs, self.app_id, should_not_run)
        self.assertIn('draft_url', result)

    def test_tracker_refuses_occupied_reserved_row(self):
        resumes.draft(self.jobs, self.app_id)
        resumes.approve(self.jobs, self.app_id)
        app_id, app = self.jobs.application(self.app_id)
        app['tracker_pending_row'] = 2
        self.jobs.save(app_id, app)
        self.cloud.rows.append(['=FORMULA()'])
        with self.assertRaisesRegex(ValueError, 'occupied'):
            tracking.track(self.jobs, self.app_id + ' --write')
        self.assertEqual(self.cloud.row_writes, 0)

    def test_original_resource_configuration_rejected(self):
        self.jobs.store.put('protected_original_ids', ['original-resume'])
        with self.assertRaisesRegex(ValueError, 'original resource'):
            self.jobs.configure('{"resume_doc_id":"original-resume"}')

    def test_reset_after_conflict_preserves_external_edit_and_invalidates_review(self):
        resumes.draft(self.jobs, self.app_id)
        resumes.suggest(self.jobs, self.app_id, lambda *args, **kwargs: {'edits': [{'before': 'Built Python ETL',
            'after': 'Built Python ETL workflows', 'source_id': 'resume-copy:source', 'quote': 'Built Python ETL'}]})
        self.cloud.doc['tabs'][1] = make_tab('draft', 'Human-reviewed external content\n')
        apply_command = json.dumps({'application_id': self.app_id, 'edit_ids': [0], 'edit_batch_id': self.jobs.application(self.app_id)[1]['suggestions']['edit_batch_id'], 'reviewed': True})
        with self.assertRaisesRegex(ValueError, 'changed after suggestions'):
            resumes.apply(self.jobs, apply_command)
        writes = self.cloud.document_writes
        with self.assertRaises(ValueError):
            resumes.reset(self.jobs, json.dumps({'application_id': self.app_id}))
        resumes.reset(self.jobs, json.dumps({'application_id': self.app_id, 'keep_current': True}))
        self.assertEqual(self.cloud.document_writes, writes)
        app = self.jobs.application(self.app_id)[1]
        self.assertEqual(app['draft']['text'], 'Human-reviewed external content\n')
        self.assertFalse(app['reviewed'])
        self.assertIsNone(app['pending_edits'])
        self.assertNotIn('suggestions', app)
        self.assertEqual(len(app['abandoned_edit_batches']), 1)
        resumes.approve(self.jobs, self.app_id)

    def test_comparison_cannot_replace_evidence_behind_existing_draft(self):
        resumes.draft(self.jobs, self.app_id)
        before = self.jobs.application(self.app_id)[1]['comparison']
        def should_not_run(*args, **kwargs):
            raise AssertionError('Comparison should stop before invoking model')
        with self.assertRaisesRegex(ValueError, 'fixed once a draft'):
            evidence.compare(self.jobs, self.app_id, should_not_run)
        self.assertEqual(self.jobs.application(self.app_id)[1]['comparison'], before)

    def test_invalid_application_id_type_is_a_validation_error(self):
        with self.assertRaisesRegex(ValueError, 'must be a string'):
            self.jobs.application(123)

    def test_apply_revalidates_cached_edits_against_current_fact_policy(self):
        resumes.draft(self.jobs,self.app_id)
        app=self.jobs.application(self.app_id)[1]
        app['suggestions']={'base_text':'Built Python ETL\n','comparison_id':app['comparison']['comparison_id'],
            'edits':[{'before':'Built Python ETL','after':'Built 100 Python ETL pipelines',
                'source_id':'resume-copy:source','quote':'Built Python ETL'}]}
        app['suggestions']['edit_batch_id']=resumes.edit_batch_id(app['suggestions'])
        self.jobs.save(self.app_id,app)
        writes=self.cloud.document_writes
        with self.assertRaisesRegex(ValueError,'numerical claims'):
            resumes.apply(self.jobs,json.dumps({'application_id':self.app_id,'edit_ids':[0],'edit_batch_id':app['suggestions']['edit_batch_id'],'reviewed':True}))
        self.assertEqual(self.cloud.document_writes,writes)

    def test_cached_letter_cannot_bypass_accepted_quote_pool(self):
        app=self.jobs.application(self.app_id)[1]
        app['cover_letter_draft']=[{'text':'I built 100 pipelines.','source_id':'resume-copy:source',
            'quote':'Built Python ETL'}]*2
        app['cover_letter_folder_id']='sandbox';self.jobs.save(self.app_id,app)
        with self.assertRaisesRegex(ValueError,'numerical claims'):
            package.cover_letter(self.jobs,self.app_id,lambda *a,**k: self.fail('Cached draft should not regenerate'))

    def test_stale_edit_selection_cannot_apply_a_new_proposal(self):
        resumes.draft(self.jobs,self.app_id)
        def proposal(after):
            return lambda *a,**k: {'edits':[{'before':'Built Python ETL','after':after,
                'source_id':'resume-copy:source','quote':'Built Python ETL'}]}
        first=json.loads(resumes.suggest(self.jobs,self.app_id,proposal('Built Python ETL workflows')))
        resumes.suggest(self.jobs,self.app_id,proposal('Built Python ETL pipelines'))
        writes=self.cloud.document_writes
        with self.assertRaisesRegex(ValueError,'current edit_batch_id'):
            resumes.apply(self.jobs,json.dumps({'application_id':self.app_id,'edit_ids':[0],
                'edit_batch_id':first['edit_batch_id'],'reviewed':True}))
        self.assertEqual(writes,self.cloud.document_writes)

    def create_letter(self):
        return package.cover_letter(self.jobs,self.app_id,lambda *a,**k:{'paragraphs':[
            {'text':'I use Python ETL.','source_id':'resume-copy:source','quote':'Built Python ETL'}]*2})

    def test_letter_requires_explicit_inclusion_and_rejects_changed_text(self):
        resumes.draft(self.jobs,self.app_id);resumes.approve(self.jobs,self.app_id);self.create_letter()
        with self.assertRaisesRegex(ValueError,'Review the current cover-letter'):
            tracking.track(self.jobs,self.app_id+' --write')
        shown=json.loads(package.show_letter(self.jobs,self.app_id))
        payload={**shown['review_template'],'decision':'approve','note':'Reviewed both paragraphs against Python ETL evidence.'}
        package.review_letter(self.jobs,json.dumps(payload))
        app=self.jobs.application(self.app_id)[1]
        self.assertEqual(package.included_letter_url(self.jobs,app),app['cover_letter_url'])
        self.cloud.extra_docs[self.app_id+'-cover']['tabs'][0]=make_tab('t0','Changed human edit\n')
        with self.assertRaisesRegex(ValueError,'text changed'):package.review_letter(self.jobs,json.dumps(payload))
        with self.assertRaisesRegex(ValueError,'Review the current cover-letter'):tracking.track(self.jobs,self.app_id+' --write')

    def test_omitted_letter_is_preserved_but_not_put_in_tracker(self):
        resumes.draft(self.jobs,self.app_id);resumes.approve(self.jobs,self.app_id);self.create_letter()
        shown=json.loads(package.show_letter(self.jobs,self.app_id))
        package.review_letter(self.jobs,json.dumps({**shown['review_template'],'decision':'omit','note':'Draft needs factual corrections.'}))
        tracking.track(self.jobs,self.app_id+' --write')
        self.assertEqual(self.cloud.rows[1][6],'')
        result=json.loads(package.summary(self.jobs,self.app_id))
        self.assertEqual(result['cover_letter'],'Omitted')
        self.assertTrue(result['cover_letter_draft'])
