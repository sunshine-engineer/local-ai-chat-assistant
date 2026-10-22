"""Output contracts passed to Ollama and validated before domain checks.

File: assistant/schemas.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

STRING = {"type": "string"}


def records(key, properties, *, minimum=0, maximum=30):
    """Build a bounded JSON schema for an array of strict records.

    Args:
        key: Stable record, schema-field or remote reconciliation key.
        properties: JSON-schema property definitions for each record.
        minimum: Minimum permitted array length.
        maximum: Maximum permitted array length.

    Returns:
        Strict JSON object/array schema.
    """
    return {
        "type": "object",
        "properties": {
            key: {
                "type": "array",
                "minItems": minimum,
                "maxItems": maximum,
                "items": {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties),
                    "additionalProperties": False,
                },
            }
        },
        "required": [key],
        "additionalProperties": False,
    }


REQUIREMENTS = {
    "type": "object",
    "properties": {
        "requirements": {"type": "array", "items": STRING, "minItems": 1, "maxItems": 30}
    },
    "required": ["requirements"],
    "additionalProperties": False,
}
MATCHES = records(
    "matches",
    {
        "requirement": STRING,
        "status": {"type": "string", "enum": ["supported", "partial", "gap"]},
        "quote": STRING,
    },
    minimum=1,
)
EDITS = records(
    "edits", {key: STRING for key in ["before", "after", "source_id", "quote"]}, maximum=20
)
LETTER = records(
    "paragraphs", {key: STRING for key in ["text", "source_id", "quote"]}, minimum=2, maximum=4
)


def matches_for(requirements, source_text):
    """Constrain match output to the selected requirements and literal quote candidates.

    Args:
        requirements: Selected literal JD requirements in their reviewed order.
        source_text: Literal text of the evidence source.

    Returns:
        JSON-schema object for this bounded model operation.
    """
    schema = records(
        "matches",
        {
            "requirement": {"type": "string", "enum": requirements},
            "status": {"type": "string", "enum": ["supported", "partial", "gap"]},
            "quote": {"type": "string", "enum": ["", *quote_candidates(source_text)]},
        },
        minimum=len(requirements),
        maximum=len(requirements),
    )
    return schema


def quote_candidates(text):
    """Enumerate distinct literal source sentences without paraphrasing them.

    Args:
        text: Text to inspect or transform without changing the original value.

    Returns:
        Ordered unique literal sentence candidates.
    """
    import re

    candidates = []
    for line in text.splitlines():
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            if sentence.strip():
                candidates.append(sentence.strip())
    return list(dict.fromkeys(candidates))


def requirements_for(jd):
    """Build a schema that permits only literal JD sentence candidates.

    Args:
        jd: Exact original job-description text.

    Returns:
        JSON-schema object for this bounded model operation.
    """
    return {
        "type": "object",
        "properties": {
            "requirements": {
                "type": "array",
                "items": {"type": "string", "enum": quote_candidates(jd)},
                "minItems": 1,
                "maxItems": 30,
            }
        },
        "required": ["requirements"],
        "additionalProperties": False,
    }


def cited_properties(sources):
    """Constrain source identifiers and quotations to supplied evidence.

    Args:
        sources: Evidence records with stable identifiers and literal source text.

    Returns:
        Source-ID and literal-quotation schema properties.
    """
    return {
        "source_id": {"type": "string", "enum": [s["id"] for s in sources]},
        "quote": {
            "type": "string",
            "enum": list(
                dict.fromkeys(q for source in sources for q in quote_candidates(source["text"]))
            ),
        },
    }


def edits_for(text, sources):
    """Build an edit schema excluding detected protected spans.

    Args:
        text: Text to inspect or transform without changing the original value.
        sources: Evidence records with stable identifiers and literal source text.

    Returns:
        JSON-schema object for this bounded model operation.
    """
    from assistant.edit_policy import protected_edit

    choices = [
        q for q in quote_candidates(text) if text.count(q) == 1 and not protected_edit(text, q)
    ]
    return records(
        "edits",
        {
            "before": {"type": "string", "enum": choices} if choices else STRING,
            "after": STRING,
            **cited_properties(sources),
        },
        maximum=20 if choices else 0,
    )


def letter_for(sources):
    """Build a bounded schema for cited cover-letter paragraphs.

    Args:
        sources: Evidence records with stable identifiers and literal source text.

    Returns:
        JSON-schema object for this bounded model operation.
    """
    return records(
        "paragraphs",
        {"text": {"type": "string", "maxLength": 1200}, **cited_properties(sources)},
        minimum=2,
        maximum=4,
    )
