import unittest
from assistant.evidence import validate_matches, validate_requirements


class EvidenceTest(unittest.TestCase):
    def test_reject_fabricated_quotes_and_missing_requirements(self):
        self.assertEqual(validate_requirements({'requirements': ['Python']}, 'Python required'), ['Python'])
        with self.assertRaises(ValueError):
            validate_requirements({'requirements': ['Kubernetes']}, 'Python required')
        for matches in [[], [{'requirement': 'Python', 'status': 'supported', 'quote': '10 years Python'}],
                        [{'requirement': 'Python', 'status': 'gap', 'quote': 'Python'}]]:
            with self.assertRaises(ValueError):
                validate_matches({'matches': matches}, ['Python'], 'Python portfolio')

    def test_explicit_gap_and_supported_quotes(self):
        result = validate_matches({'matches': [{'requirement': 'Python', 'status': 'supported', 'quote': 'Python portfolio'},
            {'requirement': 'Kubernetes', 'status': 'gap', 'quote': ''}]}, ['Python', 'Kubernetes'], 'Built Python portfolio')
        self.assertEqual(result[1]['status'], 'gap')
