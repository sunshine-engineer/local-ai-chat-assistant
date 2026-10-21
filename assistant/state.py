"""Local private workflow state, independent of chat history."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, root=None):
        self.root = Path(root or os.getenv('ASSISTANT_HOME', '.assistant')).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / 'workflow.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.path.chmod(0o600)

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM records WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO records VALUES (?, ?)', (key, json.dumps(value)))

    @contextmanager
    def action_lock(self):
        # Separate DB: state checkpoints survive a failed network call.
        with sqlite3.connect(self.root / 'lock.sqlite3', timeout=1) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
            except sqlite3.OperationalError as exc:
                raise ValueError('Another command is running; retry after it finishes.') from exc
            yield


def json_input(arguments):
    try:
        data = json.loads(arguments)
    except ValueError as exc:
        raise ValueError('Expected a JSON object. See docs/COMMANDS.md.') from exc
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object.')
    return data
