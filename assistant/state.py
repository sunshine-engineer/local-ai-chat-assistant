"""Local private workflow state, independent of chat history.

File: assistant/state.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from assistant.config import setting


class Store:
    """Persist private JSON workflow records independently from chat history."""

    def __init__(self, root=None):
        """Create the private workflow directory and initialize its SQLite record table.

        Args:
            root: Private credential or workflow directory; None uses the configured default.

        Raises:
            OSError: The private directory or database permissions cannot be set.
            sqlite3.Error: Workflow records cannot be initialized.
        """
        self.root = Path(root or setting("workflow", "home", "ASSISTANT_HOME")).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / "workflow.sqlite3"
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        # sqlite3.Connection.__exit__ commits/rolls back but does not close it.
        """Open a short-lived connection with transactional commit or rollback.

        Yields:
            Open SQLite connection.

        Raises:
            sqlite3.Error: Opening, committing or rolling back the transaction fails.
        """
        with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
            yield db

    def get(self, key, default=None):
        """Load a JSON record or return the caller's default.

        Args:
            key: Stable record, schema-field or remote reconciliation key.
            default: Fallback value when the requested record does not exist.

        Returns:
            Decoded stored value, or the supplied default.
        """
        with self.connect() as db:
            row = db.execute("SELECT value FROM records WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        """Atomically insert or replace one JSON-serializable workflow record.

        Args:
            key: Stable record, schema-field or remote reconciliation key.
            value: Value to validate, compare or persist.
        """
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO records VALUES (?, ?)", (key, json.dumps(value)))

    @contextmanager
    def action_lock(self):
        # Separate DB: state checkpoints survive a failed network call.
        """Serialize actions while allowing durable state checkpoints in a separate database.

        Yields:
            None while the exclusive local action lock is held.

        Raises:
            ValueError: Input, ownership, review state or provider output fails this operation's validation.
        """
        with closing(sqlite3.connect(self.root / "lock.sqlite3", timeout=1)) as db, db:
            try:
                db.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                raise ValueError("Another command is running; retry after it finishes.") from exc
            yield


def json_input(arguments):
    """Parse one command JSON object and report a bounded validation error.

    Args:
        arguments: Command argument string; JSON payload or application ID as required by this handler.

    Returns:
        Parsed JSON object.

    Raises:
        ValueError: Input, ownership, review state or provider output fails this operation's validation.
    """
    try:
        data = json.loads(arguments)
    except ValueError as exc:
        raise ValueError("Expected a JSON object. See docs/COMMANDS.md.") from exc
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")
    return data
