import io
import json
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator
from assistant.model import generate_json
from assistant.schemas import REQUIREMENTS, MATCHES, EDITS, LETTER


class ModelContractTest(unittest.TestCase):
    def response(self, output, **extra):
        return io.BytesIO(json.dumps({'response': json.dumps(output), 'done': True,
                                     'done_reason': 'stop', **extra}).encode())

    def test_request_uses_schema_and_disables_thinking(self):
        with patch('assistant.model.urlopen', return_value=self.response({'requirements': ['Python']})) as call:
            actual = generate_json('Extract exact quotes', {'jd': 'Python'}, schema=REQUIREMENTS)
        request = json.loads(call.call_args.args[0].data)
        self.assertEqual(request['format'], REQUIREMENTS)
        self.assertFalse(request['think'])
        self.assertFalse(request['stream'])
        self.assertIn('OUTPUT_SCHEMA', request['prompt'])
        self.assertEqual(actual, {'requirements': ['Python']})

    def test_empty_wrong_shape_and_truncated_outputs_fail(self):
        for payload, extra in [({}, {}), ({'requirements': []}, {}),
                               ({'requirements': ['Python']}, {'done_reason': 'length'}),
                               ({'requirements': ['Python']}, {'done': False})]:
            with self.subTest(payload=payload, extra=extra):
                with patch('assistant.model.urlopen', return_value=self.response(payload, **extra)):
                    with self.assertRaises(ValueError):
                        generate_json('Extract', {'jd': 'Python'}, schema=REQUIREMENTS)

    def test_output_schemas_are_valid(self):
        for schema in (REQUIREMENTS, MATCHES, EDITS, LETTER):
            Draft202012Validator.check_schema(schema)

    def test_dynamic_match_schema_bounds_count_and_literal_quotes(self):
        from assistant.schemas import matches_for, edits_for, letter_for, requirements_for
        text = 'Built Python ETL. Independent RAG project.'
        sources = [{'id': 's1', 'text': text}]
        schema = matches_for(['Python', 'Kubernetes'], text)
        Draft202012Validator.check_schema(schema)
        matches = schema['properties']['matches']
        self.assertEqual(matches['minItems'], 2)
        self.assertEqual(matches['maxItems'], 2)
        choices = matches['items']['properties']['quote']['enum']
        self.assertIn('Built Python ETL.', choices)
        self.assertNotIn('Built Python...', choices)
        Draft202012Validator.check_schema(edits_for(text, sources))
        Draft202012Validator.check_schema(letter_for(sources))
        requirement_schema = requirements_for('Required: Python and SQL. RAG is desirable.')
        Draft202012Validator.check_schema(requirement_schema)
        self.assertEqual(requirement_schema['properties']['requirements']['items']['enum'],
                         ['Required: Python and SQL.', 'RAG is desirable.'])

    def test_large_quote_contract_is_not_repeated_inside_prompt(self):
        from assistant.schemas import matches_for
        text = '\n'.join('Evidence sentence ' + str(i) + ' ' + ('word ' * 30) + '.' for i in range(40))
        schema = matches_for(['Python'], text)
        quote = schema['properties']['matches']['items']['properties']['quote']['enum'][1]
        response = {'matches': [{'requirement': 'Python', 'status': 'supported', 'quote': quote}]}
        with patch('assistant.model.urlopen', return_value=self.response(response)) as call:
            generate_json('Compare', {'source': text}, schema=schema)
        request = json.loads(call.call_args.args[0].data)
        self.assertEqual(request['format'], schema)
        self.assertNotIn('enum', request['prompt'])
        self.assertIn('Evidence sentence 0', request['prompt'])
