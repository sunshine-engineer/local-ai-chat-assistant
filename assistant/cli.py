"""Run an action without starting Streamlit: python -m assistant.cli /help."""
import sys
import os
from dotenv import load_dotenv
from assistant.runtime import build_registry


def main():
    load_dotenv()
    os.environ['ASSISTANT_CLI'] = '1'
    text = ' '.join(sys.argv[1:])
    if not sys.stdin.isatty():
        payload = sys.stdin.read().strip()
        if payload:
            text += ' ' + payload
    registry = build_registry()
    result = registry.execute(text)
    print(result if result is not None else 'Provide a command; use /help.')
    return 2 if result is None else (1 if registry.last_error else 0)


if __name__ == '__main__':
    sys.exit(main())
