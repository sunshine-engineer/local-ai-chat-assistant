"""Narrow JD-tailoring boundaries; these checks do not establish semantic truth.

File: assistant/edit_policy.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import re


def protected_spans(text):
    """Locate heuristically detected name and contact lines.

    Args:
        text: Text to inspect or transform without changing the original value.

    Returns:
        List of half-open character ranges for detected protected lines.
    """
    offset, first = 0, True
    result = []
    for line in text.splitlines(keepends=True):
        value = line.strip()
        words = value.split()
        name = (
            first
            and 2 <= len(words) <= 4
            and all(word.istitle() for word in words)
            and words[0]
            not in ("Built", "Created", "Developed", "Implemented", "Apache", "Microsoft", "Google")
        )
        contact = re.search(
            r"[\w.+-]+@[\w.-]+|https?://|www\.|(?:linkedin|github)\.com|\+?\d[\d ()-]{7,}\d",
            value,
            re.I,
        )
        if name or contact:
            result.append((offset, offset + len(line.rstrip("\r\n"))))
        if value:
            first = False
        offset += len(line)
    return result


def protected_edit(text, before):
    """Detect whether a proposed replacement intersects a protected line.

    Args:
        text: Text to inspect or transform without changing the original value.
        before: Unique original text span selected for replacement.

    Returns:
        True when the edit intersects a detected protected span.
    """
    start = text.find(before)
    return start >= 0 and any(
        start < end and start + len(before) > begin for begin, end in protected_spans(text)
    )


def new_numeric_claim(before, after, quote):
    """Detect digit-based values absent from the original span and quotation.

    Args:
        before: Unique original text span selected for replacement.
        after: Proposed replacement text.
        quote: Literal supporting quotation to inspect.

    Returns:
        True when the replacement introduces an unsupported digit-based value.
    """

    def numbers(value):
        """Extract distinct digit-based numeric values from text.

        Args:
            value: Value to validate, compare or persist.

        Returns:
            Set of distinct integer or decimal digit strings.
        """
        return set(re.findall(r"\d+(?:\.\d+)?", value))

    return bool(numbers(after) - numbers(before) - numbers(quote))
