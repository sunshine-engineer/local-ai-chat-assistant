"""Regression coverage for google.

File: tests/test_google.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import unittest
from unittest.mock import Mock

from assistant.google import FOLDER, Google


def document(text="\n"):
    """Build or return a synthetic Google document response.

    Args:
        text: Text to inspect or transform without changing the original value.

    Returns:
        Fixture value or structured response consumed by the regression.
    """
    return {
        "revisionId": "revision1",
        "tabs": [
            {
                "tabProperties": {"tabId": "t1"},
                "documentTab": {
                    "body": {
                        "content": [{"paragraph": {"elements": [{"textRun": {"content": text}}]}}]
                    }
                },
            }
        ],
    }


class MemoryGoogle(Google):
    """Provide an explicit in-memory provider double for deterministic tests."""

    def __init__(self):
        """Initialize the in-memory provider state and request counters."""
        super().__init__(".")
        self.sandbox_folder_id = "folder"
        self.text, self.created, self.writes = "\n", False, 0

    def metadata(self, file_id):
        """Return the fixture metadata required for sandbox checks.

        Args:
            file_id: Drive file identifier to inspect or authorize.

        Returns:
            Fixture value or structured response consumed by the regression.
        """
        return {"mimeType": FOLDER}

    def files(self, query):
        """Return matching fixture files without network access.

        Args:
            query: Drive file query expression.

        Returns:
            Fixture value or structured response consumed by the regression.
        """
        return [{"id": "doc"}] if self.created else []

    def call(self, method, url, **kwargs):
        """Emulate the bounded HTTP request against in-memory fixture state.

        Args:
            method: HTTP request method.
            url: Provider endpoint for the bounded operation.
            kwargs: Additional provider or test-double keyword arguments.

        Returns:
            Fixture value or structured response consumed by the regression.
        """
        self.created = True
        return {"id": "doc"}

    def document(self, doc_id):
        """Build or return a synthetic Google document response.

        Args:
            doc_id: Google document identifier.

        Returns:
            Fixture value or structured response consumed by the regression.
        """
        return document(self.text)

    def batch(self, doc_id, requests, revision):
        """Apply fixture document requests and simulate configured failures.

        Args:
            doc_id: Google document identifier.
            requests: Ordered Google Docs API update requests.
            revision: Required Google document revision identifier.
        """
        self.writes += 1
        self.text = requests[0]["insertText"]["text"] + "\n"


class GoogleTest(unittest.TestCase):
    """Exercise google contracts using isolated fixtures."""

    def test_disabled_api_diagnostic_excludes_raw_response(self):
        """Verify disabled api diagnostic excludes raw response."""
        response = Mock(ok=False, status_code=403)
        response.json.return_value = {
            "error": {
                "message": "PRIVATE RESPONSE",
                "details": [
                    {
                        "reason": "SERVICE_DISABLED",
                        "metadata": {
                            "service": "docs.googleapis.com",
                            "consumer": "PRIVATE PROJECT",
                        },
                    }
                ],
            }
        }
        session = Mock()
        session.request.return_value = response
        with self.assertRaisesRegex(ValueError, "API disabled: docs.googleapis.com") as error:
            Google(".", session).call("GET", "https://docs.googleapis.com/v1/documents/test")
        self.assertNotIn("PRIVATE", str(error.exception))

    def test_retry_reconciles_completed_remote_write(self):
        """Verify retry reconciles completed remote write."""
        google = MemoryGoogle()
        url = google.create_document("folder", "Title", "key", "Original\n")
        self.assertEqual(url, google.create_document("folder", "Title", "key", "Original\n"))
        self.assertEqual(google.writes, 1)
        google.text = "Human edit\n"
        with self.assertRaisesRegex(ValueError, "edited externally"):
            google.create_document("folder", "Title", "key", "Original\n")
        self.assertEqual(google.writes, 1)
