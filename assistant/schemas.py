"""Output contracts passed to Ollama and validated before domain checks."""
STRING = {'type': 'string'}


def records(key, properties, *, minimum=0, maximum=30):
    return {'type': 'object', 'properties': {key: {
        'type': 'array', 'minItems': minimum, 'maxItems': maximum,
        'items': {'type': 'object', 'properties': properties,
                  'required': list(properties), 'additionalProperties': False}}},
        'required': [key], 'additionalProperties': False}


REQUIREMENTS = {'type': 'object', 'properties': {'requirements': {
    'type': 'array', 'items': STRING, 'minItems': 1, 'maxItems': 30}},
    'required': ['requirements'], 'additionalProperties': False}
MATCHES = records('matches', {'requirement': STRING,
    'status': {'type': 'string', 'enum': ['supported', 'partial', 'gap']}, 'quote': STRING}, minimum=1)
EDITS = records('edits', {key: STRING for key in ['before', 'after', 'source_id', 'quote']}, maximum=20)
LETTER = records('paragraphs', {key: STRING for key in ['text', 'source_id', 'quote']}, minimum=2, maximum=4)


def matches_for(requirements, source_text):
    schema = records('matches', {'requirement': {'type': 'string', 'enum': requirements},
        'status': {'type': 'string', 'enum': ['supported', 'partial', 'gap']},
        'quote': {'type': 'string', 'enum': ['', *quote_candidates(source_text)]}},
        minimum=len(requirements), maximum=len(requirements))
    return schema


def quote_candidates(text):
    """Candidate source sentences remain exact substrings, without paraphrase/ellipsis."""
    import re
    candidates = []
    for line in text.splitlines():
        for sentence in re.split(r'(?<=[.!?])\s+', line):
            if sentence.strip():
                candidates.append(sentence.strip())
    return list(dict.fromkeys(candidates))


def requirements_for(jd):
    return {'type': 'object', 'properties': {'requirements': {
        'type': 'array', 'items': {'type': 'string', 'enum': quote_candidates(jd)},
        'minItems': 1, 'maxItems': 30}},
        'required': ['requirements'], 'additionalProperties': False}


def cited_properties(sources):
    return {'source_id': {'type': 'string', 'enum': [s['id'] for s in sources]},
            'quote': {'type': 'string', 'enum': list(dict.fromkeys(
                q for source in sources for q in quote_candidates(source['text'])))}}


def edits_for(text, sources):
    return records('edits', {'before': {'type': 'string', 'enum': [q for q in quote_candidates(text) if text.count(q) == 1]},
        'after': STRING, **cited_properties(sources)}, maximum=20)


def letter_for(sources):
    return records('paragraphs', {'text': {'type': 'string', 'maxLength': 1200}, **cited_properties(sources)}, minimum=2, maximum=4)
