"""Small public synthetic regression diagnostic; never writes to Google or workflow state."""
import json
import os
from pathlib import Path
from assistant.evidence import assess, digest
from assistant.comparison_review import flags
from assistant.model import generate_json


def failure_category(error):
    causes = []
    while error is not None and error not in causes:
        causes.append(error)
        error = error.__cause__
    if any(isinstance(cause, OSError) for cause in causes):
        return 'transport_or_service_error'
    if any(isinstance(cause, json.JSONDecodeError) for cause in causes):
        return 'invalid_json'
    if len(causes) > 1:
        return 'incomplete_or_schema_invalid_output'
    return 'domain_validation'


def evaluate(cases, model=generate_json):
    rows = []
    for case in cases:
        try:
            match = assess([case['requirement']], case['source'], case['kind'], model)[0]
            status_match = match['status'] == case['expected_status']
            quote_match = match['quote'] in case['expected_quotes']
            rows.append({'case_id': case['id'], 'valid_response': True,
                'status_matches_fixture': status_match, 'quote_matches_fixture': quote_match,
                'fixture_pass': status_match and quote_match,
                'flags': flags(case['requirement'], match['quote'], case['source'], case['kind'])})
        except ValueError as error:
            rows.append({'case_id': case['id'], 'valid_response': False, 'fixture_pass': False,
                         'failure_category': failure_category(error)})
    return {'cases': len(rows), 'fixture_passes': sum(row['fixture_pass'] for row in rows),
        'fixture_digest': digest(cases), 'policy_version': 'comparison-review-v1',
        'invalid_responses': sum(not row['valid_response'] for row in rows),
        'automatic_acceptance_enabled': False, 'results': rows,
        'limit': f'{len(rows)} synthetic known-failure regressions, not a representative benchmark. Failed/invalid cases remain in the denominator. Human comparison review is always required, regardless of this result.'}


def main():
    from dotenv import load_dotenv
    load_dotenv()
    cases = json.loads(Path(__file__).with_name('comparison_cases.json').read_text())
    report = evaluate(cases)
    report['model'] = os.getenv('OLLAMA_MODEL', 'qwen3:1.7b')
    report['context_tokens'] = int(os.getenv('OLLAMA_CONTEXT', '16384'))
    print(json.dumps(report, indent=2))
    return 0 if report['fixture_passes'] == report['cases'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
