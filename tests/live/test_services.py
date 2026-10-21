"""Opt-in checks: explicitly select this folder and point at disposable services."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from assistant.evidence import compare, digest
from assistant.jobs import Jobs
from assistant.state import Store
from assistant.requirements import review


class LiveServicesTest(unittest.TestCase):
    @unittest.skipUnless(os.getenv('ASSISTANT_LIVE_OLLAMA'), 'Set ASSISTANT_LIVE_OLLAMA for real model inference')
    def test_real_model_supported_and_missing_requirements(self):
        source = {'id': 'synthetic-resume', 'kind': 'resume', 'title': 'Synthetic resume',
            'text': 'Commercial experience: Four years building Python and SQL ETL pipelines, monitoring data quality, and troubleshooting Airflow workflows. Independent portfolio: Built a RAG document assistant with source citations and evaluation tests. No commercial GenAI deployment is claimed.',
            'doc_id': 'synthetic', 'tab_id': 't.synthetic', 'url': 'synthetic://resume'}
        jd = 'Required: Python and SQL ETL experience. Desirable: RAG portfolio projects. Required: Kubernetes production operations experience.'
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            'OLLAMA_HOST': os.environ['ASSISTANT_LIVE_OLLAMA'],
            'OLLAMA_MODEL': os.getenv('ASSISTANT_LIVE_MODEL', 'qwen3:1.7b'),
        }):
            jobs = Jobs(Store(directory))
            jobs.store.put('app:live-test', {'input': {'jd': jd}})
            jobs.store.put('catalogue', {'sources': [source], 'skipped': [], 'digest': digest([source])})
            review(jobs, json.dumps({'application_id': 'live-test', 'candidate_ids': [0, 1, 2], 'reviewed': True}))
            result = json.loads(compare(jobs, 'live-test'))
            matches = result['resumes'][0]['matches']
            self.assertTrue(any('RAG' in r for r in result['requirements']), 'Desirable requirement omitted')
            self.assertTrue(all(m['status'] == 'needs_review' for m in matches))
            self.assertIsNone(result['recommended_source_id'])
            self.assertIsNone(result['resumes'][0]['counts'])
            self.assertTrue(any('Python' in m['requirement'] and m['proposed_status'] == 'supported' for m in matches))
            self.assertTrue(any('Kubernetes' in m['requirement'] and m['proposed_status'] == 'gap' for m in matches))

    @unittest.skipUnless(os.getenv('ASSISTANT_LIVE_DATABASE_URL'), 'Set ASSISTANT_LIVE_DATABASE_URL for disposable PostgreSQL')
    def test_real_postgres_chat_persistence(self):
        from sqlalchemy.engine import make_url
        url = os.environ['ASSISTANT_LIVE_DATABASE_URL']
        self.assertEqual(make_url(url).database, 'assistant_test', 'Use a disposable database named assistant_test')
        script = '''
from helpers import create_chat_session, save_message, load_messages, get_sessions, rename_chat_session
from postgres.db import engine
sid = create_chat_session()
save_message(sid, 'user', 'Synthetic live test')
save_message(sid, 'assistant', 'Synthetic reply')
assert [m.role for m in load_messages(sid)] == ['user', 'assistant']
rename_chat_session(sid, 'Synthetic live review')
assert any(s.id == sid and s.title == 'Synthetic live review' for s in get_sessions())
engine.dispose()
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[2],
            env={**os.environ, 'DATABASE_URL': url}, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, 'PostgreSQL persistence check failed; inspect the disposable service locally.')

    @unittest.skipUnless(os.getenv('ASSISTANT_LIVE_OLLAMA'), 'Set ASSISTANT_LIVE_OLLAMA for real chat inference')
    def test_real_chat_returns_an_answer_through_streamlit(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            'OLLAMA_HOST': os.environ['ASSISTANT_LIVE_OLLAMA'],
            'OLLAMA_MODEL': os.getenv('ASSISTANT_LIVE_MODEL', 'qwen3:1.7b'),
            'ASSISTANT_HOME': directory,
            'DATABASE_URL': 'sqlite:///' + str(Path(directory) / 'chat.db'),
        }):
            root = Path(__file__).resolve().parents[2]
            app = AppTest.from_file(str(root / 'app.py')).run(timeout=30)
            self.assertFalse(app.exception)
            app.chat_input[0].set_value('Reply with exactly READY').run(timeout=180)
            self.assertFalse(app.exception)
            self.assertTrue(any(item.value.strip() == 'READY' for item in app.markdown), 'Real model did not return READY')
            from postgres.db import engine
            engine.dispose()
