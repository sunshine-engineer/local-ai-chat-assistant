"""Regression coverage for evidence.

File: tests/test_evidence.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import unittest

from assistant.evidence import validate_matches, validate_requirements


class EvidenceTest(unittest.TestCase):
    """Exercise evidence contracts using isolated fixtures."""

    def test_reject_fabricated_quotes_and_missing_requirements(self):
        """Verify reject fabricated quotes and missing requirements."""
        self.assertEqual(
            validate_requirements({"requirements": ["Python"]}, "Python required"), ["Python"]
        )
        with self.assertRaises(ValueError):
            validate_requirements({"requirements": ["Kubernetes"]}, "Python required")
        for matches in [
            [],
            [{"requirement": "Python", "status": "supported", "quote": "10 years Python"}],
            [{"requirement": "Python", "status": "gap", "quote": "Python"}],
        ]:
            with self.assertRaises(ValueError):
                validate_matches({"matches": matches}, ["Python"], "Python portfolio")

    def test_explicit_gap_and_supported_quotes(self):
        """Verify explicit gap and supported quotes."""
        result = validate_matches(
            {
                "matches": [
                    {"requirement": "Python", "status": "supported", "quote": "Python portfolio"},
                    {"requirement": "Kubernetes", "status": "gap", "quote": ""},
                ]
            },
            ["Python", "Kubernetes"],
            "Built Python portfolio",
        )
        self.assertEqual(result[1]["status"], "gap")
