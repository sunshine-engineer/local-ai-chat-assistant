"""Narrow JD-tailoring boundaries; these checks do not establish semantic truth."""
import re


def protected_spans(text):
    offset, first = 0, True
    result = []
    for line in text.splitlines(keepends=True):
        value = line.strip()
        words = value.split()
        name = (first and 2 <= len(words) <= 4 and all(word.istitle() for word in words)
                and words[0] not in ('Built', 'Created', 'Developed', 'Implemented', 'Apache', 'Microsoft', 'Google'))
        contact = re.search(r'[\w.+-]+@[\w.-]+|https?://|www\.|(?:linkedin|github)\.com|\+?\d[\d ()-]{7,}\d', value, re.I)
        if name or contact:
            result.append((offset, offset + len(line.rstrip('\r\n'))))
        if value:
            first = False
        offset += len(line)
    return result


def protected_edit(text, before):
    start = text.find(before)
    return start >= 0 and any(start < end and start + len(before) > begin for begin, end in protected_spans(text))


def new_numeric_claim(before, after, quote):
    numbers = lambda value: set(re.findall(r'\d+(?:\.\d+)?', value))
    return bool(numbers(after) - numbers(before) - numbers(quote))
